"""
Servidor FastAPI con WebSocket bidireccional para streaming en tiempo real
"""
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Set
import time
import uuid
import sys
import os
import logging

# Agregar path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, TradingPair, SignalBotConfig, SignalBotSelectedPair
from datetime import datetime, timezone, timedelta

from .config import settings
from .candles import CandleStore, MultiTimeframeAggregator, Candle
from .indicators import IndicatorEngine
from .price_poller import TwelveDataPoller
from .history_loader import load_historical_candles
from strategies.tablero_binarias_strategy import TableroBinariasStrategy


# Configurar logging estructurado para producción
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("realtime_server")


app = FastAPI(title="STC RealTime Trading")

# Configurar CORS con dominios específicos para producción
replit_domains = os.getenv('REPLIT_DOMAINS', '')
ALLOWED_ORIGINS = ["http://localhost:5000"]  # Desarrollo local

# Parsear REPLIT_DOMAINS (puede contener múltiples dominios separados por coma)
if replit_domains:
    for domain in replit_domains.split(','):
        domain = domain.strip()
        if domain:
            ALLOWED_ORIGINS.append(f"https://{domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ AUTENTICACIÓN ============

# API Key obligatoria (sin fallback inseguro)
API_KEY = os.getenv("BOT_API_KEY")
if not API_KEY:
    raise RuntimeError("BOT_API_KEY no configurada. Configure el secreto en Replit antes de iniciar.")

async def verify_api_key(authorization: str = Header(None)) -> bool:
    """Verifica que la petición incluya API key válida"""
    if not authorization:
        raise HTTPException(status_code=401, detail="API key requerida")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de autorización inválido")
    
    api_key = authorization.split("Bearer ")[1]
    
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API key inválida")
    
    return True


# ============ FUNCIONES HELPER PARA BASE DE DATOS ============

def get_available_trading_pairs() -> List[str]:
    """Obtiene lista de símbolos de pares de trading activos desde BD - Solo EURUSD y EURJPY"""
    try:
        with get_db() as db:
            # Solo permitir EURUSD y EURJPY
            pairs = db.query(TradingPair).filter(
                TradingPair.is_active == True,
                TradingPair.symbol.in_(["EURUSD", "EURJPY"])
            ).order_by(TradingPair.display_order).all()
            symbols = [pair.symbol for pair in pairs]
            
            # Fallback si no hay pares en BD
            if not symbols:
                return ["EURUSD", "EURJPY"]
            
            return symbols
    except Exception as e:
        logger.error(f"Error obteniendo pares de trading: {e}")
        # Fallback a valores por defecto si falla BD - Solo EURUSD y EURJPY
        return ["EURUSD", "EURJPY"]


def get_real_candles_from_db(symbol: str, timeframe: str = "M5", limit: int = 100) -> List[Candle]:
    """
    Obtiene velas REALES de Twelve Data desde PostgreSQL (las mismas del gráfico)
    
    Args:
        symbol: Símbolo del par (ej: "EURUSD")
        timeframe: Timeframe de BD (ej: "M5") - usa formato BD
        limit: Cantidad de velas a obtener (default: 100)
    
    Returns:
        Lista de velas ordenadas cronológicamente (más antiguas primero)
    """
    from sqlalchemy import text
    
    try:
        with get_db() as db:
            # Query SQL directo para obtener últimas N velas de Twelve Data
            query = text("""
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE symbol = :symbol 
                  AND timeframe = :timeframe
                  AND (broker = 'twelvedata' OR source = 'twelvedata')
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            result = db.execute(query, {
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit
            })
            
            rows = result.fetchall()
            
            if not rows:
                logger.warning(f"No se encontraron velas en BD para {symbol} {timeframe}")
                return []
            
            # Convertir a objetos Candle (ordenar cronológicamente: más antiguas primero)
            candles = []
            for row in reversed(rows):  # Invertir para orden cronológico
                candle = Candle(
                    start_ts=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]) if row[5] else 0.0
                )
                candles.append(candle)
            
            logger.info(f"Cargadas {len(candles)} velas desde BD para {symbol} {timeframe}")
            return candles
            
    except Exception as e:
        logger.error(f"Error leyendo velas de BD: {e}")
        return []


def load_bot_config_from_db(user_id: str = None) -> dict:
    """Carga configuración del bot desde BD (global si user_id=None)"""
    try:
        with get_db() as db:
            config = db.query(SignalBotConfig).filter(SignalBotConfig.user_id == user_id).first()
            
            if not config:
                # Crear configuración por defecto si no existe
                config = SignalBotConfig(
                    user_id=user_id,
                    scanning_active=False,
                    max_gales=7,
                    initial_stake=10.0,
                    multiplier=2.0
                )
                db.add(config)
                db.commit()
                
                # Agregar todos los pares por defecto
                all_pairs = db.query(TradingPair).filter(TradingPair.is_active == True).all()
                for pair in all_pairs:
                    selected_pair = SignalBotSelectedPair(config_id=config.id, pair_id=pair.id)
                    db.add(selected_pair)
                db.commit()
                logger.info("Configuración global creada")
            
            # Obtener símbolos seleccionados
            selected_symbols = []
            for selected_pair in config.selected_pairs:
                selected_symbols.append(selected_pair.trading_pair.symbol)
            
            return {
                "scanning_active": config.scanning_active,
                "selected_symbols": selected_symbols,
                "martingale_config": {
                    "max_gales": config.max_gales,
                    "initial_stake": config.initial_stake,
                    "multiplier": config.multiplier
                }
            }
    except Exception as e:
        logger.error(f"Error cargando configuración: {e}")
        # Fallback a configuración por defecto - Solo EURUSD y EURJPY
        return {
            "scanning_active": False,
            "selected_symbols": ["EURUSD", "EURJPY"],
            "martingale_config": {
                "max_gales": 7,
                "initial_stake": 10.0,
                "multiplier": 2.0
            }
        }


def save_bot_config_to_db(user_id: str, config_data: dict) -> bool:
    """Guarda configuración del bot en BD"""
    try:
        with get_db() as db:
            config = db.query(SignalBotConfig).filter(SignalBotConfig.user_id == user_id).first()
            
            if not config:
                config = SignalBotConfig(user_id=user_id)
                db.add(config)
                db.flush()  # Para obtener el ID
            
            # Actualizar campos
            if "scanning_active" in config_data:
                config.scanning_active = config_data["scanning_active"]
                if config_data["scanning_active"]:
                    config.last_started_at = datetime.utcnow()
                else:
                    config.last_stopped_at = datetime.utcnow()
            
            if "martingale_config" in config_data:
                mg_config = config_data["martingale_config"]
                if "max_gales" in mg_config:
                    config.max_gales = mg_config["max_gales"]
                if "initial_stake" in mg_config:
                    config.initial_stake = mg_config["initial_stake"]
                if "multiplier" in mg_config:
                    config.multiplier = mg_config["multiplier"]
            
            # Actualizar pares seleccionados
            if "selected_symbols" in config_data:
                # Eliminar selecciones anteriores
                db.query(SignalBotSelectedPair).filter(SignalBotSelectedPair.config_id == config.id).delete()
                
                # Agregar nuevas selecciones
                for symbol in config_data["selected_symbols"]:
                    pair = db.query(TradingPair).filter(TradingPair.symbol == symbol).first()
                    if pair:
                        selected_pair = SignalBotSelectedPair(config_id=config.id, pair_id=pair.id)
                        db.add(selected_pair)
            
            db.commit()
            logger.info(f"Configuración guardada para usuario: {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")
        return False


# Estado global
class TradingState:
    def __init__(self):
        # Símbolos disponibles en el sistema (desde BD)
        self.symbols = get_available_trading_pairs()
        
        # Cargar configuración desde BD (global)
        bot_config = load_bot_config_from_db(None)
        
        # Control de escaneo y configuración del bot
        # SIEMPRE inicia INACTIVO - usuario debe activar manualmente
        self.scanning_active = False
        self.selected_symbols = bot_config["selected_symbols"]
        self.martingale_config = bot_config["martingale_config"]
        
        # SÍMBOLO ACTIVO: Solo 1 a la vez (por defecto EURUSD)
        self.active_symbol = "EURUSD"
        
        # Almacenamiento multi-timeframe
        self.aggregator = MultiTimeframeAggregator(base_interval_sec=60)
        
        # Agregar timeframes soportados para cada símbolo (500 velas de histórico)
        for symbol in self.symbols:
            self.aggregator.add_timeframe(symbol, 1, max_history=500)  # 1m
            self.aggregator.add_timeframe(symbol, 5, max_history=500)  # 5m
            self.aggregator.add_timeframe(symbol, 15, max_history=500)  # 15m
        
        # Motor de indicadores por símbolo
        self.indicators: Dict[str, IndicatorEngine] = {}
        for symbol in self.symbols:
            engine = IndicatorEngine()
            engine.add_ema("EMA20", 20)
            engine.add_ema("EMA50", 50)
            engine.add_rsi("RSI14", 14)
            engine.add_macd("MACD", 12, 26, 9)
            self.indicators[symbol] = engine
        
        # Estrategia de señales por símbolo y timeframe
        self.strategies: Dict[str, TableroBinariasStrategy] = {}
        for symbol in self.symbols:
            key = f"{symbol}_5m"  # Señales en M5
            self.strategies[key] = TableroBinariasStrategy()
        
        # Señales activas {symbol: {direction, confidence, expires_at, sequence_id}}
        self.active_signals: Dict[str, dict] = {}
        
        # Clientes WebSocket conectados
        self.clients: Set[WebSocket] = set()
        
        # Cliente Twelve Data (Poller REST API)
        self.twelvedata_client: TwelveDataPoller = None
        self.twelvedata_task: asyncio.Task = None

state = TradingState()


async def check_signal_result_and_gale(symbol: str, closed_candle, tick_ts: int):
    """
    Verifica el resultado de la señal activa cuando cierra vela M5
    y gestiona el ciclo de Martingale (Gales)
    """
    if symbol not in state.active_signals:
        return None
    
    # Validar que la vela cerrada exista
    if closed_candle is None:
        return None
    
    active_signal = state.active_signals[symbol]
    
    # Verificar si la vela que cerró corresponde al período de la señal
    # La señal fue generada en generated_at, expira en expires_at
    # Si se cerró una vela M5, verificar si es tiempo de evaluar
    vela_cierre_ts = closed_candle.start_ts + 300  # start_ts + 5min
    
    # Solo procesar si el cierre de vela es el que corresponde a la señal
    # (es decir, la vela que cerró >= expires_at de la señal)
    if vela_cierre_ts < active_signal["expires_at"]:
        return None
    
    # Determinar resultado de la operación
    direction = active_signal["direction"]
    entry_price = active_signal["entry_price"]
    close_price = float(closed_candle.close)
    
    # Calcular si ganó o perdió
    if direction == "CALL":
        won = close_price > entry_price
    else:  # PUT
        won = close_price < entry_price
    
    gale_level = len(active_signal["gale_cycle"])
    
    if won:
        # Agregar última operación ganadora al ciclo
        utc_minus_4 = timezone(timedelta(hours=-4))
        time_str = datetime.fromtimestamp(tick_ts, tz=utc_minus_4).strftime("%H:%M")
        active_signal["gale_cycle"].append({
            "level": gale_level,
            "result": "WIN",
            "price": close_price,
            "timestamp": tick_ts,
            "time_str": time_str
        })
        
        # Marcar como completado y listo para reiniciar
        active_signal["completed"] = True
        active_signal["final_result"] = "WIN"
        
        # Limpiar señal después de 10 segundos para mostrar el resultado
        return {
            "type": "gale_result",
            "symbol": symbol,
            "result": "WIN",
            "gale_level": gale_level,
            "signal": active_signal
        }
    else:
        # ❌ PERDIÓ - Iniciar siguiente Gale
        utc_minus_4 = timezone(timedelta(hours=-4))
        time_str = datetime.fromtimestamp(tick_ts, tz=utc_minus_4).strftime("%H:%M")
        
        # Agregar operación perdida al ciclo
        active_signal["gale_cycle"].append({
            "level": gale_level,
            "result": "LOSS",
            "price": close_price,
            "timestamp": tick_ts,
            "time_str": time_str
        })
        
        # Verificar si alcanzó el máximo de gales configurado
        max_gales = state.martingale_config["max_gales"]
        if len(active_signal["gale_cycle"]) > max_gales:
            active_signal["completed"] = True
            active_signal["final_result"] = "LOSS_MAX_GALES"
            
            return {
                "type": "gale_result",
                "symbol": symbol,
                "result": "LOSS_MAX_GALES",
                "gale_level": max_gales,
                "signal": active_signal
            }
        
        # Continuar con siguiente Gale
        # La vela que ACABÓ DE CERRAR es closed_candle
        # La próxima vela cierra en: closed_candle.start_ts + 600 (siguiente vela M5)
        expires_at = closed_candle.start_ts + 600
        
        active_signal["expires_at"] = expires_at
        active_signal["entry_price"] = close_price  # Precio de entrada = cierre de vela anterior
        active_signal["current_price"] = close_price
        
        return {
            "type": "gale_continue",
            "symbol": symbol,
            "gale_level": len(active_signal["gale_cycle"]),
            "signal": active_signal
        }


async def clean_up_signal_after_delay(symbol: str, signal_id: int, delay_seconds: int = 10):
    """
    Tarea en background para limpiar señal después de un delay sin bloquear el loop principal
    """
    await asyncio.sleep(delay_seconds)
    
    # Verificar que la señal actual sea la misma que cuando se inició el cleanup
    if symbol in state.active_signals:
        current_signal = state.active_signals[symbol]
        if id(current_signal) == signal_id:
            del state.active_signals[symbol]


async def generate_signal_if_closed(symbol: str, closed_candles: Dict, tick_ts: int):
    """
    Genera señal si se cerró una vela M5
    
    LÓGICA CORRECTA:
    1. Analiza dirección probabilística (CALL/PUT) con Markov/Tablero Binarias
    2. Detecta color de vela cerrada: VERDE (close > open) o ROJA (close < open)
    3. Si vela VERDE + dirección coincide → Nueva señal
    4. Si vela ROJA → Cuenta velas rojas consecutivas = Nivel de Gale
    """
    if not closed_candles.get("5m"):
        return None
    
    # Verificar si el bot está activo y si este es el símbolo activo
    if not state.scanning_active:
        return None
    
    # SNAPSHOT del símbolo activo (para evitar race conditions)
    active_symbol_snapshot = state.active_symbol
    
    # SOLO generar señales para el símbolo activo (no para todos)
    if symbol != active_symbol_snapshot:
        return None
    
    closed_candle_m5 = closed_candles["5m"]
    
    # Primero verificar si hay señal activa y evaluar su resultado
    gale_msg = await check_signal_result_and_gale(symbol, closed_candle_m5, tick_ts)
    if gale_msg:
        # Enviar actualización de gale INMEDIATAMENTE (para que usuario vea resultado)
        await broadcast([gale_msg])
        
        # Si el ciclo terminó (ganó o perdió máximo de gales)
        if gale_msg.get("type") == "gale_result":
            # Si GANÓ → Limpiar señal INMEDIATAMENTE para generar nueva vela tras vela
            if gale_msg.get("result") == "WIN":
                if symbol in state.active_signals:
                    del state.active_signals[symbol]
                logger.info(f"✅ {symbol} ganó - Limpiando señal para continuar vela tras vela")
            else:
                # Si PERDIÓ (max gales) → Programar cleanup con delay para mostrar resultado
                signal_ref = state.active_signals.get(symbol)
                if signal_ref:
                    signal_id = id(signal_ref)
                    asyncio.create_task(clean_up_signal_after_delay(symbol, signal_id, 10))
    
    # Solo generar nueva señal si NO hay señal activa
    if symbol in state.active_signals:
        return None
    
    # Obtener últimas 100 velas M5 REALES de la BD (Twelve Data Time Series)
    tf_key = f"{symbol}_5m"
    real_candles_from_db = get_real_candles_from_db(symbol, "M5", limit=100)
    
    if len(real_candles_from_db) < 10:
        return None
    
    # Obtener vela ACTUAL construida desde ticks (en formación)
    if tf_key not in state.aggregator.stores:
        return None
    
    store = state.aggregator.stores[tf_key]
    current_candle_from_ticks = store.candles[-1] if store.candles else None
    
    if not current_candle_from_ticks:
        return None
    
    # 3. Combinar: Velas reales (historial) + Vela actual (en formación)
    candles_history = real_candles_from_db + [current_candle_from_ticks]
    
    # 4. Ejecutar estrategia con velas correctas
    strategy = state.strategies.get(tf_key)
    if not strategy:
        return None
    
    # Convertir velas a formato Strategy
    from strategy_engine import Candle as StrategyCandle
    strategy_candles = [
        StrategyCandle(
            time=c.start_ts,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume
        )
        for c in candles_history
    ]
    
    # Calcular indicadores
    indicators = strategy.calculate_indicators(strategy_candles)
    
    # Generar señal probabilística (dirección sugerida)
    signal = strategy.generate_signal(strategy_candles, indicators)
    
    if not signal or signal.direction == 'HOLD':
        return None
    
    # Detectar color de vela cerrada
    closed_candle = candles_history[-1]
    candle_color = "GREEN" if closed_candle.close > closed_candle.open else "RED"
    
    # Validar coincidencia entre color de vela y dirección de señal
    if candle_color == "GREEN":
        if signal.direction != "CALL":
            return None
    else:  # RED
        if signal.direction != "PUT":
            return None
    
    # Generar nueva señal (solo si pasó la validación de color)
    entry_price = float(closed_candle.close)
    current_price = float(closed_candle.close)
    
    # Calcular tiempo de expiración sincronizado con cierre de vela M5
    candle_ts = int(closed_candle.start_ts)
    new_candle_start = candle_ts + 300  # +5 minutos = inicio de nueva vela
    expires_at = new_candle_start + 300  # +5 minutos más = cierre de la nueva vela
    generated_at = new_candle_start
    
    signal_data = {
        "type": "signal",
        "symbol": symbol,
        "timeframe": "5m",
        "direction": signal.direction,
        "confidence": float(signal.confidence),
        "entry_price": entry_price,
        "current_price": current_price,
        "generated_at": generated_at,
        "expires_at": expires_at,
        "sequence_id": str(uuid.uuid4()),
        "is_valid": True,
        "gale_cycle": [],  # Nueva señal, ciclo vacío
        "completed": False,
        "indicators": signal.indicators,
        "candle_color": candle_color  # Agregar color de vela para referencia
    }
    
    # Guardar señal activa
    state.active_signals[symbol] = signal_data
    
    # Calcular campos para broadcast
    total_duration = 5 * 60
    time_elapsed = tick_ts - generated_at
    progress_percent = min(100, max(0, (time_elapsed / total_duration) * 100))
    time_remaining = expires_at - tick_ts
    
    is_winning = current_price > entry_price if signal.direction == "CALL" else current_price < entry_price
    
    broadcast_data = {
        **signal_data,
        'progress_percent': round(progress_percent, 1),
        'time_remaining': time_remaining,
        'is_winning': is_winning,
        'expired': False
    }
    
    await broadcast([broadcast_data])
    logger.info(f"Señal enviada a {len(state.clients)} clientes conectados")
    
    return signal_data


def validate_signal_status(signal: dict, current_price: float, current_ts: int) -> dict:
    """
    Valida el estado de una señal activa
    - Actualiza precio actual
    - Verifica si sigue vigente (ganando/perdiendo)
    - Detecta si expiró y si ganó o perdió
    """
    signal["current_price"] = current_price
    
    # Validar vigencia según dirección
    entry_price = signal["entry_price"]
    direction = signal["direction"]
    
    if direction == "CALL":
        # CALL vigente si precio actual > precio entrada (ganando)
        signal["is_winning"] = current_price > entry_price
    else:  # PUT
        # PUT vigente si precio actual < precio entrada (ganando)
        signal["is_winning"] = current_price < entry_price
    
    # Verificar si expiró (5 minutos completos)
    if current_ts >= signal["expires_at"]:
        signal["expired"] = True
        # Determinar resultado final
        if signal["is_winning"]:
            signal["result"] = "WIN"
        else:
            signal["result"] = "LOSS"
    else:
        signal["expired"] = False
    
    return signal


async def on_price_tick(symbol: str, price: float, tick_ts: int):
    """
    Callback cuando llega un nuevo tick desde Twelve Data
    """
    # Actualizar estado de señal activa si existe
    if symbol in state.active_signals:
        state.active_signals[symbol] = validate_signal_status(
            state.active_signals[symbol], 
            price, 
            tick_ts
        )
    
    # Procesar tick en todos los timeframes
    closed_candles = state.aggregator.process_tick(symbol, price, tick_ts)
    
    # Actualizar OHLC de vela M5 actual en señal activa
    if symbol in state.active_signals:
        tf_key_m5 = f"{symbol}_5m"
        if tf_key_m5 in state.aggregator.stores:
            store_m5 = state.aggregator.stores[tf_key_m5]
            current_m5 = store_m5.get_current_candle()
            
            if current_m5 and all([
                current_m5.open is not None,
                current_m5.high is not None,
                current_m5.low is not None,
                current_m5.close is not None
            ]):
                # Agregar OHLC de vela M5 actual a la señal
                state.active_signals[symbol]["current_ohlc"] = {
                    "open": float(current_m5.open),
                    "high": float(current_m5.high),
                    "low": float(current_m5.low),
                    "close": float(current_m5.close),
                    "timestamp": current_m5.start_ts
                }
                
                # DEBUG: Mostrar valores OHLC y color detectado
                is_green = current_m5.close > current_m5.open
                color_str = "🟢 VERDE" if is_green else "🔴 ROJA"
                # Debug OHLC removed
    
    # Actualizar indicadores del símbolo específico
    indicators_values = None
    if symbol in state.indicators:
        indicators_values = state.indicators[symbol].update(price)
    
    # Generar señal si se cerró vela M5
    signal_msg = await generate_signal_if_closed(symbol, closed_candles, tick_ts)
    
    # Obtener vela actual para cada timeframe
    messages = []
    
    for tf_key, store in state.aggregator.stores.items():
        if store.symbol == symbol:
            timeframe = tf_key.split('_')[1]
            current_candle = store.get_current_candle()
            
            if current_candle:
                # Validar que la vela tenga valores válidos
                if all([
                    current_candle.start_ts is not None,
                    current_candle.open is not None and current_candle.open > 0,
                    current_candle.high is not None and current_candle.high > 0,
                    current_candle.low is not None and current_candle.low > 0,
                    current_candle.close is not None and current_candle.close > 0
                ]):
                    # Mensaje de vela en construcción
                    candle_msg = {
                        "type": "candle",
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "data": {
                            "time": current_candle.start_ts,
                            "open": float(current_candle.open),
                            "high": float(current_candle.high),
                            "low": float(current_candle.low),
                            "close": float(current_candle.close),
                            "volume": current_candle.volume,
                            "final": current_candle.final
                        }
                    }
                    messages.append(candle_msg)
                
                    # Si la vela se cerró, notificar también con la vela cerrada correcta
                    if closed_candles.get(timeframe):
                        closed_candle = closed_candles[timeframe]
                        # Validar vela cerrada
                        if all([
                            closed_candle.start_ts is not None,
                            closed_candle.open is not None and closed_candle.open > 0,
                            closed_candle.high is not None and closed_candle.high > 0,
                            closed_candle.low is not None and closed_candle.low > 0,
                            closed_candle.close is not None and closed_candle.close > 0
                        ]):
                            closed_msg = {
                                "type": "candle_closed",
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "data": {
                                    "time": closed_candle.start_ts,
                                    "open": float(closed_candle.open),
                                    "high": float(closed_candle.high),
                                    "low": float(closed_candle.low),
                                    "close": float(closed_candle.close),
                                    "volume": closed_candle.volume,
                                    "final": True
                                }
                            }
                            messages.append(closed_msg)
    
    # Mensaje de indicadores (solo para 1m)
    if indicators_values:
        indicators_msg = {
            "type": "indicators",
            "symbol": symbol,
            "timeframe": "1m",
            "time": tick_ts,
            "data": indicators_values
        }
        messages.append(indicators_msg)
    
    # Agregar señal si se generó
    if signal_msg:
        messages.append(signal_msg)
    
    # Broadcast a todos los clientes
    await broadcast(messages)


async def broadcast(messages: List[dict]):
    """Envía mensajes a todos los clientes conectados"""
    if not state.clients:
        return
    
    # Agregar timestamp del servidor (UTC) a cada mensaje
    server_time_ms = int(time.time() * 1000)
    
    disconnected = set()
    
    for client in state.clients:
        try:
            for msg in messages:
                # Agregar server_time a cada mensaje para sincronización
                msg_with_time = {**msg, "server_time": server_time_ms}
                await client.send_json(msg_with_time)
        except Exception as e:
            logger.warning(f"Error enviando a cliente: {e}")
            disconnected.add(client)
    
    # Limpiar clientes desconectados
    state.clients -= disconnected


async def load_historical_data():
    """Carga datos históricos en segundo plano (no bloquea startup)"""
    # Mapeo de símbolos para históricos
    symbol_map_history = {
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "EURJPY": "EUR/JPY"
    }
    
    logger.info(f"📊 Cargando velas históricas para {len(state.symbols)} símbolos")
    
    for symbol in state.symbols:
        symbol_td = symbol_map_history.get(symbol, "EUR/USD")
        # Loading symbol
        
        # Cargar histórico para cada timeframe
        history_1m = await load_historical_candles(symbol_td, "1min", 500)
        history_5m = await load_historical_candles(symbol_td, "5min", 500)
        history_15m = await load_historical_candles(symbol_td, "15min", 500)
        
        # Poblar stores 1m
        if history_1m:
            for candle_data in history_1m:
                candle = Candle(
                    start_ts=candle_data["time"],
                    open=candle_data["open"],
                    high=candle_data["high"],
                    low=candle_data["low"],
                    close=candle_data["close"],
                    final=True,
                    volume=0
                )
                state.aggregator.stores[f"{symbol}_1m"].candles.append(candle)
                # Actualizar indicadores del símbolo específico
                if symbol in state.indicators:
                    state.indicators[symbol].update(candle_data["close"])
        
        # Poblar stores 5m
        if history_5m:
            for candle_data in history_5m:
                candle = Candle(
                    start_ts=candle_data["time"],
                    open=candle_data["open"],
                    high=candle_data["high"],
                    low=candle_data["low"],
                    close=candle_data["close"],
                    final=True,
                    volume=0
                )
                state.aggregator.stores[f"{symbol}_5m"].candles.append(candle)
        
        # Poblar stores 15m
        if history_15m:
            for candle_data in history_15m:
                candle = Candle(
                    start_ts=candle_data["time"],
                    open=candle_data["open"],
                    high=candle_data["high"],
                    low=candle_data["low"],
                    close=candle_data["close"],
                    final=True,
                    volume=0
                )
                state.aggregator.stores[f"{symbol}_15m"].candles.append(candle)
        
        logger.info(f"{symbol}: 1m({len(history_1m)}), 5m({len(history_5m)}), 15m({len(history_15m)})")
    
    logger.info("✅ Datos históricos cargados completamente")


@app.on_event("startup")
async def startup_event():
    """Inicia el servidor FastAPI - RÁPIDO para que Replit detecte el puerto"""
    logger.info("🚀 Iniciando servidor de trading en tiempo real")
    
    # Validar configuración con manejo de errores explícito
    try:
        settings.validate()
        logger.info("✅ Configuración validada correctamente")
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        raise
    
    # Crear cliente Twelve Data (Poller) con múltiples símbolos
    state.twelvedata_client = TwelveDataPoller(
        on_price_callback=on_price_tick,
        symbols=state.symbols
    )
    
    logger.info(f"⚡ Servidor iniciado - puerto abierto")
    
    # Cargar datos históricos y iniciar polling EN SEGUNDO PLANO
    # Esto permite que Uvicorn abra el puerto inmediatamente
    asyncio.create_task(load_historical_data())
    
    # Iniciar tarea de polling (sin esperar a que termine la carga histórica)
    state.twelvedata_task = asyncio.create_task(state.twelvedata_client.run())
    
    logger.info(f"📡 Polling iniciado para {len(state.symbols)} símbolos (cada 1s)")


@app.on_event("shutdown")
async def shutdown_event():
    """Detiene el cliente Twelve Data al cerrar FastAPI"""
    logger.info("Deteniendo servidor")
    
    if state.twelvedata_client:
        await state.twelvedata_client.stop()
    
    if state.twelvedata_task:
        state.twelvedata_task.cancel()
    
    logger.info("Servidor detenido")


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para clientes frontend"""
    await websocket.accept()
    state.clients.add(websocket)
    
    logger.info(f"Cliente conectado - Total: {len(state.clients)}")
    
    try:
        # Enviar histórico inicial para todos los timeframes
        for tf_key, store in state.aggregator.stores.items():
            timeframe = tf_key.split('_')[1]
            history = store.get_history()
            
            if history:
                # Filtrar solo velas válidas (sin valores null)
                # NO filtrar por timestamp futuro - son velas históricas confiables de API
                valid_history = [
                    candle for candle in history
                    if candle.get('time') is not None
                    and candle.get('open') is not None and candle.get('open') > 0
                    and candle.get('high') is not None and candle.get('high') > 0
                    and candle.get('low') is not None and candle.get('low') > 0
                    and candle.get('close') is not None and candle.get('close') > 0
                ]
                
                # Ordenar por timestamp para garantizar orden cronológico
                valid_history.sort(key=lambda x: x.get('time', 0))
                
                invalid_count = len(history) - len(valid_history)
                if invalid_count > 0:
                    # Filtered invalid candles
                    # Mostrar primera vela filtrada
                    for candle in history:
                        if not (candle.get('time') is not None
                            and candle.get('open') is not None and candle.get('open') > 0
                            and candle.get('high') is not None and candle.get('high') > 0
                            and candle.get('low') is not None and candle.get('low') > 0
                            and candle.get('close') is not None and candle.get('close') > 0):
                            # Null candle debug
                            break
                
                if valid_history:
                    logger.info(f"Enviando {len(valid_history)} velas {timeframe}")
                    await websocket.send_json({
                        "type": "init_candles",
                        "symbol": store.symbol,
                        "timeframe": timeframe,
                        "data": valid_history
                    })
                else:
                    logger.warning(f"No hay velas válidas en {timeframe}")
        
        # Enviar indicadores iniciales (solo para EURUSD por compatibilidad)
        if "EURUSD" in state.indicators:
            indicators_values = state.indicators["EURUSD"].get_values()
            if indicators_values:
                await websocket.send_json({
                    "type": "init_indicators",
                    "symbol": "EURUSD",
                    "data": indicators_values
                })
        
        # 📡 Enviar señales activas existentes al cliente recién conectado
        if state.active_signals:
            current_time = int(time.time())
            for symbol, signal_data in state.active_signals.items():
                # Solo enviar señales que no han expirado
                if signal_data.get('expires_at', 0) > current_time:
                    # Calcular progreso y tiempo restante
                    total_duration = 5 * 60
                    time_elapsed = current_time - (signal_data['expires_at'] - total_duration)
                    progress_percent = min(100, max(0, (time_elapsed / total_duration) * 100))
                    time_remaining = signal_data['expires_at'] - current_time
                    
                    # Determinar si está ganando
                    current_price = signal_data.get('current_price', signal_data['entry_price'])
                    entry_price = signal_data['entry_price']
                    direction = signal_data['direction']
                    is_winning = current_price > entry_price if direction == "CALL" else current_price < entry_price
                    
                    # Enviar con campos de UI
                    await websocket.send_json({
                        **signal_data,
                        'progress_percent': round(progress_percent, 1),
                        'time_remaining': time_remaining,
                        'is_winning': is_winning,
                        'expired': False
                    })
                    logger.info(f"Enviada señal activa {symbol} a nuevo cliente")
        
        # Mantener conexión abierta
        while True:
            data = await websocket.receive_text()
            # Aquí podrías manejar mensajes del cliente si es necesario
            # Por ahora solo mantiene la conexión
            
    except WebSocketDisconnect:
        state.clients.discard(websocket)
        logger.info(f"Cliente desconectado - Total: {len(state.clients)}")
    except Exception as e:
        state.clients.discard(websocket)
        logger.error(f"Error en WebSocket cliente: {e}")


@app.get("/api/signals/live")
async def get_live_signals():
    """Endpoint para obtener todas las señales activas"""
    current_time = int(time.time())
    active = []
    
    # Filtrar señales que no han expirado
    for symbol, signal_data in state.active_signals.items():
        if signal_data.get('expires_at', 0) > current_time:
            # Calcular tiempo restante y progreso
            total_duration = 5 * 60  # 5 minutos en segundos
            time_elapsed = current_time - (signal_data['expires_at'] - total_duration)
            progress_percent = min(100, max(0, (time_elapsed / total_duration) * 100))
            time_remaining = signal_data['expires_at'] - current_time
            
            active.append({
                **signal_data,
                'progress_percent': round(progress_percent, 1),
                'time_remaining': time_remaining
            })
    
    return JSONResponse({
        "status": "ok",
        "signals": active,
        "timestamp": current_time
    })


@app.get("/api/status")
async def status():
    """Endpoint de estado del servidor"""
    return JSONResponse({
        "status": "online",
        "clients_connected": len(state.clients),
        "symbols": state.symbols,
        "timeframes": settings.SUPPORTED_TIMEFRAMES,
        "active_signals": len(state.active_signals),
        "candles_per_symbol": {
            symbol: {
                "1m": state.aggregator.stores.get(f"{symbol}_1m", {}).get_candles_count() if f"{symbol}_1m" in state.aggregator.stores else 0,
                "5m": state.aggregator.stores.get(f"{symbol}_5m", {}).get_candles_count() if f"{symbol}_5m" in state.aggregator.stores else 0,
                "15m": state.aggregator.stores.get(f"{symbol}_15m", {}).get_candles_count() if f"{symbol}_15m" in state.aggregator.stores else 0,
            }
            for symbol in state.symbols
        }
    })


@app.get("/api/bot/status")
async def get_bot_status():
    """Obtener estado actual del bot y configuración"""
    return JSONResponse({
        "status": "ok",
        "bot": {
            "scanning_active": state.scanning_active,
            "selected_symbols": state.selected_symbols,
            "martingale_config": state.martingale_config,
            "active_signals_count": len(state.active_signals)
        }
    })


async def generate_immediate_signal_for_symbol(symbol: str) -> dict:
    """Genera señal inmediata para un símbolo usando la vela M5 actual"""
    import time
    from strategy_engine import Candle as StrategyCandle
    
    # Obtener historial de velas M5 (incluyendo la vela actual)
    tf_key = f"{symbol}_5m"
    if tf_key not in state.aggregator.stores:
        return None
    
    store = state.aggregator.stores[tf_key]
    candles_history = store.candles
    
    if len(candles_history) < 10:
        return None
    
    # Ejecutar estrategia
    strategy = state.strategies.get(tf_key)
    if not strategy:
        return None
    
    # Convertir velas a formato Strategy
    strategy_candles = [
        StrategyCandle(
            time=c.start_ts,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume
        )
        for c in candles_history
    ]
    
    # Calcular indicadores
    indicators = strategy.calculate_indicators(strategy_candles)
    
    # Generar señal
    signal = strategy.generate_signal(strategy_candles, indicators)
    
    if not signal or signal.direction == 'HOLD':
        return None
    
    # Obtener vela M5 ACTUAL (la última, que se está formando)
    current_candle = candles_history[-1]
    
    # VALIDACIÓN DE COLOR DE VELA: Detectar si la vela actual es verde o roja
    candle_color = "GREEN" if current_candle.close > current_candle.open else "RED"
    
    # Vela color analysis
    # Strategy direction
    
    # LÓGICA DE VALIDACIÓN:
    # - Vela VERDE + Dirección CALL → Generar señal ✓
    # - Vela ROJA + Dirección PUT → Generar señal ✓
    # - Cualquier otra combinación → NO generar señal ✗
    
    if candle_color == "GREEN":
        if signal.direction != "CALL":
            # Validation skip
            return None
        # Validation ok
    else:  # RED
        if signal.direction != "PUT":
            # Validation skip
            return None
        # Validation ok
    
    # Precio de entrada = precio ACTUAL (close de la vela que se está formando)
    entry_price = float(current_candle.close)
    current_price = float(current_candle.close)
    
    # Timestamp de generación
    generated_at = int(time.time())
    
    # SOLUCIÓN: Generar señal para la PRÓXIMA vela M5
    # Calcular el próximo múltiplo de 300 segundos (5 minutos)
    now = int(time.time())
    current_period_start = (now // 300) * 300
    next_period_start = current_period_start + 300
    
    # expires_at es el cierre de la PRÓXIMA vela M5 (next_period_start ya ES el cierre)
    expires_at = next_period_start
    
    signal_data = {
        "type": "signal",
        "symbol": symbol,
        "timeframe": "5m",
        "direction": signal.direction,
        "confidence": float(signal.confidence),
        "entry_price": entry_price,
        "current_price": current_price,
        "generated_at": generated_at,
        "expires_at": expires_at,
        "sequence_id": str(uuid.uuid4()),
        "is_valid": True,
        "gale_cycle": [],
        "completed": False,
        "indicators": signal.indicators,
        "candle_color": candle_color
    }
    
    # VERIFICACIÓN FINAL: Asegurar que el símbolo siga siendo el activo antes de guardar
    # (Protección contra race condition si cambió durante la ejecución)
    if symbol != state.active_symbol:
        logger.warning(f"{symbol} - Símbolo activo cambió durante generación")
        return None
    
    # Guardar señal activa
    state.active_signals[symbol] = signal_data
    
    logger.info(f"Señal generada: {symbol} {signal.direction} (confianza: {signal.confidence:.1%})")
    # Entry price debug
    
    return signal_data


@app.post("/api/bot/start")
async def start_bot(authorized: bool = Depends(verify_api_key)):
    """Iniciar escaneo de señales (requiere autenticación)"""
    if state.scanning_active:
        return JSONResponse({
            "status": "error",
            "message": "El bot ya está activo"
        }, status_code=400)
    
    state.scanning_active = True
    logger.info(f"Bot iniciado - Escaneando {len(state.selected_symbols)} pares")
    
    # Generar señales INMEDIATAS para todos los símbolos seleccionados
    immediate_signals = []
    for symbol in state.selected_symbols:
        signal_data = await generate_immediate_signal_for_symbol(symbol)
        if signal_data:
            immediate_signals.append(signal_data)
    
    # Guardar en BD
    save_bot_config_to_db(None, {"scanning_active": True})
    
    # Broadcast estado del bot
    await broadcast([{
        "type": "bot_status",
        "scanning_active": True,
        "message": "Bot iniciado correctamente"
    }])
    
    # Broadcast señales inmediatas a todos los clientes
    if immediate_signals:
        for signal_data in immediate_signals:
            import time
            tick_ts = int(time.time())
            total_duration = 5 * 60
            time_elapsed = tick_ts - signal_data["generated_at"]
            progress_percent = min(100, max(0, (time_elapsed / total_duration) * 100))
            time_remaining = signal_data["expires_at"] - tick_ts
            
            is_winning = signal_data["current_price"] > signal_data["entry_price"] if signal_data["direction"] == "CALL" else signal_data["current_price"] < signal_data["entry_price"]
            
            broadcast_data = {
                **signal_data,
                'progress_percent': round(progress_percent, 1),
                'time_remaining': time_remaining,
                'is_winning': is_winning,
                'expired': False
            }
            
            await broadcast([broadcast_data])
            logger.info(f"Señal enviada: {signal_data['symbol']}")
    
    return JSONResponse({
        "status": "ok",
        "message": "Bot iniciado correctamente",
        "scanning_active": True,
        "immediate_signals_generated": len(immediate_signals)
    })


@app.post("/api/bot/stop")
async def stop_bot(authorized: bool = Depends(verify_api_key)):
    """Detener escaneo de señales (requiere autenticación)"""
    if not state.scanning_active:
        return JSONResponse({
            "status": "error",
            "message": "El bot ya está detenido"
        }, status_code=400)
    
    state.scanning_active = False
    logger.info("Bot detenido")
    
    # Limpiar todas las señales activas
    cleared_symbols = list(state.active_signals.keys())
    state.active_signals.clear()
    if cleared_symbols:
        logger.info(f"Señales limpiadas: {cleared_symbols}")
    
    # Guardar en BD
    save_bot_config_to_db(None, {"scanning_active": False})
    
    # Broadcast a todos los clientes
    messages = [{
        "type": "bot_status",
        "scanning_active": False,
        "message": "Bot detenido"
    }]
    
    # Agregar mensaje de limpieza de señales para cada símbolo
    for symbol in cleared_symbols:
        messages.append({
            "type": "signal_cleared",
            "symbol": symbol
        })
    
    await broadcast(messages)
    
    return JSONResponse({
        "status": "ok",
        "message": "Bot detenido correctamente",
        "scanning_active": False,
        "cleared_signals": cleared_symbols
    })


@app.post("/api/bot/config")
async def configure_bot(request: Request, authorized: bool = Depends(verify_api_key)):
    """Configurar pares y Martingale (requiere autenticación)"""
    try:
        data = await request.json()
        
        # Validar que el payload sea un diccionario
        if not isinstance(data, dict):
            return JSONResponse({
                "status": "error",
                "message": "Payload inválido: debe ser un objeto JSON"
            }, status_code=400)
        
        # Constantes de validación (cargar desde BD)
        VALID_SYMBOLS = get_available_trading_pairs()
        MAX_GALES_MIN = 0
        MAX_GALES_MAX = 10
        MIN_STAKE = 0.01
        MAX_STAKE = 100000
        MIN_MULTIPLIER = 1.0
        MAX_MULTIPLIER = 10.0
        
        # Actualizar pares seleccionados
        if "selected_symbols" in data:
            symbols = data["selected_symbols"]
            
            # Validar tipo de datos
            if not isinstance(symbols, list):
                return JSONResponse({
                    "status": "error",
                    "message": "selected_symbols debe ser una lista"
                }, status_code=400)
            
            # Validar que no esté vacía
            if not symbols:
                return JSONResponse({
                    "status": "error",
                    "message": "Debe seleccionar al menos un par"
                }, status_code=400)
            
            # Validar que todos los elementos sean strings
            if not all(isinstance(s, str) for s in symbols):
                return JSONResponse({
                    "status": "error",
                    "message": "Todos los símbolos deben ser strings"
                }, status_code=400)
            
            # Validar que los símbolos existan en la lista válida
            invalid = [s for s in symbols if s not in VALID_SYMBOLS]
            if invalid:
                return JSONResponse({
                    "status": "error",
                    "message": f"Símbolos inválidos: {invalid}. Válidos: {VALID_SYMBOLS}"
                }, status_code=400)
            
            state.selected_symbols = symbols
            logger.info(f"Pares actualizados: {symbols}")
        
        # Actualizar configuración de Martingale
        if "martingale_config" in data:
            config = data["martingale_config"]
            
            # Validar que sea un diccionario
            if not isinstance(config, dict):
                return JSONResponse({
                    "status": "error",
                    "message": "martingale_config debe ser un objeto"
                }, status_code=400)
            
            # Validar max_gales
            if "max_gales" in config:
                try:
                    max_gales = int(config["max_gales"])
                except (ValueError, TypeError):
                    return JSONResponse({
                        "status": "error",
                        "message": "max_gales debe ser un número entero"
                    }, status_code=400)
                
                if max_gales < MAX_GALES_MIN or max_gales > MAX_GALES_MAX:
                    return JSONResponse({
                        "status": "error",
                        "message": f"max_gales debe estar entre {MAX_GALES_MIN} y {MAX_GALES_MAX}"
                    }, status_code=400)
                
                state.martingale_config["max_gales"] = max_gales
            
            # Validar initial_stake
            if "initial_stake" in config:
                try:
                    initial_stake = float(config["initial_stake"])
                except (ValueError, TypeError):
                    return JSONResponse({
                        "status": "error",
                        "message": "initial_stake debe ser un número"
                    }, status_code=400)
                
                if initial_stake < MIN_STAKE or initial_stake > MAX_STAKE:
                    return JSONResponse({
                        "status": "error",
                        "message": f"initial_stake debe estar entre {MIN_STAKE} y {MAX_STAKE}"
                    }, status_code=400)
                
                state.martingale_config["initial_stake"] = initial_stake
            
            # Validar multiplier
            if "multiplier" in config:
                try:
                    multiplier = float(config["multiplier"])
                except (ValueError, TypeError):
                    return JSONResponse({
                        "status": "error",
                        "message": "multiplier debe ser un número"
                    }, status_code=400)
                
                if multiplier < MIN_MULTIPLIER or multiplier > MAX_MULTIPLIER:
                    return JSONResponse({
                        "status": "error",
                        "message": f"multiplier debe estar entre {MIN_MULTIPLIER} y {MAX_MULTIPLIER}"
                    }, status_code=400)
                
                state.martingale_config["multiplier"] = multiplier
            
            logger.info("Martingale actualizado")
        
        # Guardar configuración en BD
        save_bot_config_to_db(None, data)
        
        # Broadcast a todos los clientes
        await broadcast([{
            "type": "bot_config_updated",
            "selected_symbols": state.selected_symbols,
            "martingale_config": state.martingale_config
        }])
        
        return JSONResponse({
            "status": "ok",
            "message": "Configuración actualizada correctamente",
            "config": {
                "selected_symbols": state.selected_symbols,
                "martingale_config": state.martingale_config
            }
        })
    
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error de validación: {str(e)}"
        }, status_code=400)
    
    except Exception as e:
        logger.error(f"Error configurando bot: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error interno del servidor: {str(e)}"
        }, status_code=500)


@app.post("/api/bot/change-symbol")
async def change_active_symbol(request: Request):
    """Cambiar símbolo activo (sin autenticación para facilitar UX)"""
    try:
        data = await request.json()
        symbol = data.get("symbol")
        
        if not symbol:
            return JSONResponse({
                "status": "error",
                "message": "Símbolo requerido"
            }, status_code=400)
        
        # Validar que el símbolo sea válido
        if symbol not in state.symbols:
            return JSONResponse({
                "status": "error",
                "message": f"Símbolo inválido: {symbol}. Válidos: {state.symbols}"
            }, status_code=400)
        
        # Cambiar símbolo activo
        old_symbol = state.active_symbol
        state.active_symbol = symbol
        logger.info(f"Símbolo activo cambiado: {old_symbol} → {symbol}")
        
        # CRÍTICO: Limpiar señal del símbolo anterior para evitar señales atoradas
        if old_symbol in state.active_signals:
            logger.info(f"Limpiando señal de {old_symbol}")
            # Notificar a los clientes que la señal fue cancelada
            await broadcast([{
                "type": "signal_cancelled",
                "symbol": old_symbol,
                "reason": "symbol_changed"
            }])
            del state.active_signals[old_symbol]
        
        # Broadcast a todos los clientes
        await broadcast([{
            "type": "active_symbol_changed",
            "symbol": symbol
        }])
        
        return JSONResponse({
            "status": "ok",
            "message": f"Símbolo activo cambiado a {symbol}",
            "active_symbol": symbol
        })
    
    except Exception as e:
        logger.error(f"Error cambiando símbolo: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error interno: {str(e)}"
        }, status_code=500)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {"message": "STC RealTime Trading Server", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
