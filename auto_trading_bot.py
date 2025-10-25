"""
Bot de Auto-Trading - STC Trading System
Ejecuta trades automáticamente basado en señales de estrategias
"""

import time
import threading
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable
from datetime import datetime
from strategy_engine import Strategy, StrategyEngine, Candle, Signal, Trade
import uuid
from database import get_db, Bot as BotModel, BotStat, Trade as TradeModel


@dataclass
class BotConfig:
    """Configuración de un bot de trading"""
    name: str
    strategy_name: str
    symbol: str
    timeframe: str
    trade_amount: float
    trade_duration: int
    max_daily_loss: float
    max_daily_trades: int
    active: bool = False
    auto_restart: bool = True
    use_dual_gale: bool = False


@dataclass
class BotStats:
    """Estadísticas de un bot de trading"""
    bot_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    daily_profit: float = 0.0
    total_profit: float = 0.0
    win_rate: float = 0.0
    last_trade_time: Optional[int] = None
    trades_today: int = 0
    last_signal: Optional[Signal] = None
    status: str = 'idle'
    error_message: Optional[str] = None
    
    def update_stats(self, trade: Trade):
        """Actualiza estadísticas después de un trade"""
        self.total_trades += 1
        self.trades_today += 1
        
        if trade.result == 'WIN':
            self.winning_trades += 1
            self.daily_profit += trade.profit
            self.total_profit += trade.profit
        elif trade.result == 'LOSS':
            self.losing_trades += 1
            self.daily_profit += trade.profit
            self.total_profit += trade.profit
            
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            
        self.last_trade_time = trade.entry_time
        
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_profit = 0.0
        self.trades_today = 0
        
    def to_dict(self) -> dict:
        return {
            'bot_id': self.bot_id,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'daily_profit': round(self.daily_profit, 2),
            'total_profit': round(self.total_profit, 2),
            'win_rate': round(self.win_rate, 2),
            'last_trade_time': self.last_trade_time,
            'trades_today': self.trades_today,
            'status': self.status,
            'error_message': self.error_message
        }


class TradingBot:
    """Bot de trading automatizado con sistema de gales simple"""
    
    GALE_AMOUNTS = [5.00, 10.75, 23.15, 49.75, 106.90, 229.80, 494.00, 1061.80]
    
    def __init__(
        self, 
        bot_id: str,
        config: BotConfig,
        strategy: Strategy,
        trade_executor: Callable,
        candle_provider: Callable,
        result_checker: Optional[Callable] = None,
        save_callback: Optional[Callable] = None,
        trade_saver: Optional[Callable] = None
    ):
        self.bot_id = bot_id
        self.config = config
        self.strategy = strategy
        self.trade_executor = trade_executor
        self.candle_provider = candle_provider
        self.result_checker = result_checker
        self.save_callback = save_callback
        self.trade_saver = trade_saver
        
        self.stats = BotStats(bot_id=bot_id)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.trades: List[Trade] = []
        
        self.gale_level = 0
        self.last_direction = None
        self.pending_trade = None
        self.last_candle_time = 0
        
    def start(self):
        """Inicia el bot"""
        if self.running:
            return
            
        self.running = True
        self.config.active = True
        self.stats.status = 'running'
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        print(f"🤖 Bot iniciado: {self.config.name} ({self.bot_id})")
        
    def stop(self):
        """Detiene el bot"""
        self.running = False
        self.config.active = False
        self.stats.status = 'stopped'
        
        if self.thread:
            self.thread.join(timeout=5)
            
        print(f"🛑 Bot detenido: {self.config.name} ({self.bot_id})")
        
    def _run_loop(self):
        """Loop principal del bot con sistema de gales"""
        print(f"🚀 {self.config.name} - Loop iniciado con sistema de gales")
        
        while self.running:
            try:
                if self._should_stop_trading():
                    self.stats.status = 'paused'
                    time.sleep(60)
                    continue
                
                candles = self.candle_provider(
                    self.config.symbol, 
                    self.config.timeframe
                )
                
                if not candles or len(candles) < self.strategy.min_candles:
                    time.sleep(1)
                    continue
                
                current_candle_time = candles[-1].time
                current_timestamp = int(time.time())
                
                if current_candle_time != self.last_candle_time:
                    print(f"🕐 Nueva vela detectada: {current_candle_time} (Gale {self.gale_level})")
                    
                    if self.pending_trade:
                        self._check_trade_result(candles, current_timestamp)
                    elif not self.pending_trade:
                        self._process_new_candle(candles, current_timestamp)
                    
                    self.last_candle_time = current_candle_time
                
                self.stats.status = 'running'
                time.sleep(1)
                
            except Exception as e:
                self.stats.status = 'error'
                self.stats.error_message = str(e)
                print(f"❌ Error en bot {self.config.name}: {e}")
                
                if not self.config.auto_restart:
                    self.stop()
                else:
                    time.sleep(30)
                    
    def _should_stop_trading(self) -> bool:
        """Verifica si el bot debe dejar de operar"""
        if self.stats.daily_profit <= -self.config.max_daily_loss:
            return True
            
        if self.stats.trades_today >= self.config.max_daily_trades:
            return True
            
        return False
    
    def _process_new_candle(self, candles: List[Candle], current_timestamp: int):
        """Procesa nueva vela: analiza señal y espera al inicio exacto de la próxima vela M5"""
        signal = self.strategy.analyze(
            self.config.symbol,
            self.config.timeframe,
            candles
        )
        
        # LÓGICA TRADINGVIEW: Si estrategia genera señal CALL/PUT, ejecutar sin filtro de confidence
        if signal and signal.direction in ['CALL', 'PUT']:
            # El bot mantiene su PROPIO contador de Martingala independiente
            # NO usar el gale_level de la estrategia para controlar el estado del bot
            is_gale = signal.indicators.get('is_gale', False)
            signal_gale_level = signal.indicators.get('gale_level', 0)
            
            # Usar el gale_level INTERNO del bot para determinar el monto
            amount = self.GALE_AMOUNTS[min(self.gale_level, 7)]
            
            if self.gale_level > 0:
                # Bot está en secuencia de martingala
                print(f"🔵 Bot en GALE {self.gale_level}: {signal.direction} (confidence: {signal.confidence:.1%})")
                if is_gale and signal_gale_level > 0:
                    print(f"   Estrategia también detectó Gale {signal_gale_level} (info)")
            else:
                # Operación normal Gale 0
                print(f"🎯 Señal detectada: {signal.direction} (confidence: {signal.confidence:.1%})")
                if is_gale and signal_gale_level > 0:
                    print(f"   Estrategia detectó Gale {signal_gale_level}, pero bot está en Gale 0 (post-WIN)")
            
            # ESPERAR hasta el inicio EXACTO de la próxima vela M5
            self._wait_and_execute_at_next_candle(signal.direction, amount, current_timestamp)
        else:
            print(f"⚪ Sin señal válida en esta vela")
    
    def _check_trade_result(self, candles: List[Candle], current_timestamp: int):
        """Verifica resultado del trade pendiente por color de vela"""
        if not self.pending_trade:
            return
        
        trade = self.pending_trade
        
        if current_timestamp < trade['expiry_time']:
            return
        
        expiry_candle_time = (trade['expiry_time'] // 300) * 300
        result_candle = None
        
        for candle in reversed(candles):
            if candle.time == expiry_candle_time:
                result_candle = candle
                break
        
        if not result_candle:
            result_candle = candles[-2] if len(candles) >= 2 else candles[-1]
        
        print(f"🔍 Verificando resultado de {trade['direction']} Gale {self.gale_level}")
        print(f"   Ejecutado: {trade['entry_time']} | Expira: {trade['expiry_time']}")
        print(f"   Vela resultado: {result_candle.time}")
        print(f"   Open: {result_candle.open:.5f}, Close: {result_candle.close:.5f}")
        
        is_green = result_candle.close > result_candle.open
        is_red = result_candle.close < result_candle.open
        
        print(f"   Vela {'VERDE ↑' if is_green else 'ROJA ↓' if is_red else 'DOJI'}")
        
        won = (trade['direction'] == 'CALL' and is_green) or (trade['direction'] == 'PUT' and is_red)
        
        if won:
            profit = trade['amount'] * 0.87
            print(f"✅ WIN - {trade['direction']} Gale {self.gale_level} - Profit: +${profit:.2f}")
            
            self.stats.winning_trades += 1
            self.stats.total_trades += 1
            self.stats.daily_profit += profit
            self.stats.total_profit += profit
            
            if self.trade_saver:
                self.trade_saver(self.bot_id, {
                    'direction': trade['direction'],
                    'amount': trade['amount'],
                    'gale_level': self.gale_level,
                    'entry_time': trade['entry_time'],
                    'expiry_time': trade['expiry_time'],
                    'entry_price': result_candle.open,
                    'exit_price': result_candle.close,
                    'result': 'WIN',
                    'profit': profit,
                    'symbol': self.config.symbol,
                    'timeframe': self.config.timeframe,
                    'strategy_name': self.config.strategy_name
                })
            
            self.gale_level = 0
            self.last_direction = None
            if self.save_callback:
                self.save_callback()
            
            print(f"🔍 Verificando si vela actual tiene señal...")
            signal = self.strategy.analyze(
                self.config.symbol,
                self.config.timeframe,
                candles
            )
            
            if signal and signal.direction in ['CALL', 'PUT'] and signal.confidence >= 0.5:
                print(f"🎯 ¡Señal válida en vela actual! {signal.direction} (confidence: {signal.confidence:.2f})")
                self.last_direction = signal.direction
                
                current_candle_start = candles[-1].time
                self._execute_trade_at_candle_start(signal.direction, self.GALE_AMOUNTS[0], current_candle_start)
            else:
                print(f"⚪ Sin señal válida - esperando próxima vela")
                self.pending_trade = None
        else:
            loss = -trade['amount']
            print(f"❌ LOSS - {trade['direction']} Gale {self.gale_level} - Loss: ${loss:.2f}")
            
            self.stats.losing_trades += 1
            self.stats.total_trades += 1
            self.stats.daily_profit += loss
            self.stats.total_profit += loss
            
            if self.trade_saver:
                self.trade_saver(self.bot_id, {
                    'direction': trade['direction'],
                    'amount': trade['amount'],
                    'gale_level': self.gale_level,
                    'entry_time': trade['entry_time'],
                    'expiry_time': trade['expiry_time'],
                    'entry_price': result_candle.open,
                    'exit_price': result_candle.close,
                    'result': 'LOSS',
                    'profit': loss,
                    'symbol': self.config.symbol,
                    'timeframe': self.config.timeframe,
                    'strategy_name': self.config.strategy_name
                })
            
            if self.gale_level < 7:
                self.gale_level += 1
                print(f"🔄 Avanzando a Gale {self.gale_level}")
                if self.save_callback:
                    self.save_callback()
                
                print(f"🔍 Verificando si vela actual tiene señal para Gale {self.gale_level}...")
                signal = self.strategy.analyze(
                    self.config.symbol,
                    self.config.timeframe,
                    candles
                )
                
                if signal and signal.direction in ['CALL', 'PUT'] and signal.confidence >= 0.5:
                    print(f"🎯 ¡Señal válida en vela actual! {signal.direction} (confidence: {signal.confidence:.2f})")
                    self.last_direction = signal.direction
                    
                    current_candle_start = candles[-1].time
                    self._execute_trade_at_candle_start(signal.direction, self.GALE_AMOUNTS[self.gale_level], current_candle_start)
                else:
                    print(f"⚪ Sin señal válida - esperando próxima vela con señal")
                    self.pending_trade = None
            else:
                print(f"🛑 Secuencia completa perdida - Reset a Gale 0")
                self.gale_level = 0
                self.last_direction = None
                if self.save_callback:
                    self.save_callback()
        
        if self.stats.total_trades > 0:
            self.stats.win_rate = (self.stats.winning_trades / self.stats.total_trades) * 100
        
    def _wait_and_execute_at_next_candle(self, direction: str, amount: float, current_timestamp: int):
        """Espera hasta el inicio EXACTO de la próxima vela M5 y ejecuta"""
        # Calcular el inicio de la próxima vela M5 (múltiplo de 300 segundos)
        next_candle_start = ((current_timestamp // 300) + 1) * 300
        seconds_to_wait = next_candle_start - current_timestamp
        
        print(f"⏳ Esperando {seconds_to_wait}s hasta próxima vela M5...")
        print(f"   Hora actual: {time.strftime('%H:%M:%S', time.localtime(current_timestamp))}")
        print(f"   Ejecución programada: {time.strftime('%H:%M:%S', time.localtime(next_candle_start))}")
        
        # Esperar hasta 1 segundo ANTES del inicio de la vela
        if seconds_to_wait > 1:
            time.sleep(seconds_to_wait - 1)
        
        # Esperar activamente hasta el segundo exacto
        while time.time() < next_candle_start:
            time.sleep(0.05)  # Check cada 50ms
        
        # EJECUTAR en el segundo 0 de la vela
        self._execute_trade_at_candle_start(direction, amount, next_candle_start)
    
    def _execute_trade_at_candle_start(self, direction: str, amount: float, candle_start_time: int):
        """Ejecuta un trade al inicio de una vela M5"""
        try:
            entry_time = candle_start_time
            expiry_time = entry_time + (self.config.trade_duration * 60)
            
            print(f"📤 Ejecutando operación: ${amount:.2f} {direction} en {self.config.symbol} (5 min)")
            print(f"   Entry: {entry_time} | Expiry: {expiry_time}")
            print(f"   ⏰ Hora de ejecución: {time.strftime('%H:%M:%S', time.localtime())}")
            
            result = self.trade_executor(
                symbol=self.config.symbol,
                direction=direction,
                amount=amount,
                duration=self.config.trade_duration
            )
            
            if result.get('success'):
                self.pending_trade = {
                    'direction': direction,
                    'amount': amount,
                    'gale_level': self.gale_level,
                    'entry_time': entry_time,
                    'expiry_time': expiry_time,
                    'timestamp': time.time()
                }
                print(f"✅ Operación enviada a IQ Option")
            else:
                print(f"❌ Error enviando operación: {result.get('message', 'Desconocido')}")
                
        except Exception as e:
            print(f"❌ Error ejecutando trade: {e}")
    
            
    def get_config(self) -> dict:
        """Retorna la configuración del bot"""
        return {
            'bot_id': self.bot_id,
            'name': self.config.name,
            'strategy_name': self.config.strategy_name,
            'symbol': self.config.symbol,
            'timeframe': self.config.timeframe,
            'trade_amount': self.config.trade_amount,
            'trade_duration': self.config.trade_duration,
            'max_daily_loss': self.config.max_daily_loss,
            'max_daily_trades': self.config.max_daily_trades,
            'active': self.config.active,
            'auto_restart': self.config.auto_restart
        }


class BotManager:
    """Gestor de bots de trading - Usa PostgreSQL para persistencia"""
    
    def __init__(self, strategy_engine: StrategyEngine):
        self.strategy_engine = strategy_engine
        self.bots: Dict[str, TradingBot] = {}
        self.trade_executor: Optional[Callable] = None
        self.candle_provider: Optional[Callable] = None
        self.result_checker: Optional[Callable] = None
        
    def set_trade_executor(self, executor: Callable):
        """Configura la función para ejecutar trades"""
        self.trade_executor = executor
        
    def set_candle_provider(self, provider: Callable):
        """Configura la función para obtener velas"""
        self.candle_provider = provider
    
    def set_result_checker(self, checker: Callable):
        """Configura la función para verificar resultados de trades"""
        self.result_checker = checker
        
    def save_trade(self, bot_id: str, trade_data: dict):
        """Guarda un trade en la base de datos con protección anti-duplicados"""
        try:
            with get_db() as db:
                # PROTECCIÓN ANTI-DUPLICADOS: Verificar si ya existe
                existing_trade = db.query(TradeModel).filter(
                    TradeModel.bot_id == bot_id,
                    TradeModel.entry_time == trade_data['entry_time'],
                    TradeModel.gale_level == trade_data.get('gale_level', 0)
                ).first()
                
                if existing_trade:
                    print(f"⚠️ Trade duplicado detectado y bloqueado:")
                    print(f"   Bot: {bot_id} | Entry: {trade_data['entry_time']} | Gale: {trade_data.get('gale_level', 0)}")
                    print(f"   Ya existe en BD con ID: {existing_trade.id}")
                    return
                
                # Si no existe, guardar normalmente
                trade = TradeModel(
                    bot_id=bot_id,
                    direction=trade_data['direction'],
                    amount=trade_data['amount'],
                    gale_level=trade_data.get('gale_level', 0),
                    entry_time=trade_data['entry_time'],
                    expiry_time=trade_data['expiry_time'],
                    entry_price=trade_data.get('entry_price'),
                    exit_price=trade_data.get('exit_price'),
                    result=trade_data.get('result'),
                    profit=trade_data.get('profit', 0.0),
                    symbol=trade_data['symbol'],
                    timeframe=trade_data['timeframe'],
                    strategy_name=trade_data['strategy_name']
                )
                db.add(trade)
                print(f"✅ Trade guardado correctamente (Gale {trade_data.get('gale_level', 0)})")
        except Exception as e:
            print(f"❌ Error guardando trade en DB: {e}")
    
    def _save_bots(self):
        """Guarda la configuración de todos los bots en base de datos PostgreSQL"""
        try:
            with get_db() as db:
                for bot_id, bot in self.bots.items():
                    bot_model = db.query(BotModel).filter(BotModel.id == bot_id).first()
                    
                    if bot_model:
                        bot_model.name = bot.config.name
                        bot_model.strategy_name = bot.config.strategy_name
                        bot_model.symbol = bot.config.symbol
                        bot_model.timeframe = bot.config.timeframe
                        bot_model.trade_amount = bot.config.trade_amount
                        bot_model.trade_duration = bot.config.trade_duration
                        bot_model.max_daily_loss = bot.config.max_daily_loss
                        bot_model.max_daily_trades = bot.config.max_daily_trades
                        bot_model.active = bot.config.active
                        bot_model.auto_restart = bot.config.auto_restart
                        bot_model.gale_level = bot.gale_level
                        bot_model.last_direction = bot.last_direction
                        bot_model.pending_trade = bot.pending_trade
                        bot_model.last_candle_time = bot.last_candle_time
                    else:
                        bot_model = BotModel(
                            id=bot_id,
                            user_id=getattr(bot, 'user_id', None),
                            name=bot.config.name,
                            strategy_name=bot.config.strategy_name,
                            symbol=bot.config.symbol,
                            timeframe=bot.config.timeframe,
                            trade_amount=bot.config.trade_amount,
                            trade_duration=bot.config.trade_duration,
                            max_daily_loss=bot.config.max_daily_loss,
                            max_daily_trades=bot.config.max_daily_trades,
                            active=bot.config.active,
                            auto_restart=bot.config.auto_restart,
                            use_dual_gale=bot.config.use_dual_gale,
                            gale_level=bot.gale_level,
                            last_direction=bot.last_direction,
                            pending_trade=bot.pending_trade,
                            last_candle_time=bot.last_candle_time
                        )
                        db.add(bot_model)
                    
                    stat_model = db.query(BotStat).filter(BotStat.bot_id == bot_id).first()
                    if stat_model:
                        stat_model.total_trades = bot.stats.total_trades
                        stat_model.winning_trades = bot.stats.winning_trades
                        stat_model.losing_trades = bot.stats.losing_trades
                        stat_model.daily_profit = bot.stats.daily_profit
                        stat_model.total_profit = bot.stats.total_profit
                        stat_model.win_rate = bot.stats.win_rate
                        stat_model.trades_today = bot.stats.trades_today
                        stat_model.last_trade_time = bot.stats.last_trade_time or 0
                        stat_model.status = bot.stats.status
                        stat_model.error_message = bot.stats.error_message
                    else:
                        stat_model = BotStat(
                            bot_id=bot_id,
                            total_trades=bot.stats.total_trades,
                            winning_trades=bot.stats.winning_trades,
                            losing_trades=bot.stats.losing_trades,
                            daily_profit=bot.stats.daily_profit,
                            total_profit=bot.stats.total_profit,
                            win_rate=bot.stats.win_rate,
                            trades_today=bot.stats.trades_today,
                            last_trade_time=bot.stats.last_trade_time or 0,
                            status=bot.stats.status,
                            error_message=bot.stats.error_message
                        )
                        db.add(stat_model)
                
            print(f"💾 Bots guardados en PostgreSQL: {len(self.bots)} bots")
        except Exception as e:
            print(f"❌ Error guardando bots en DB: {e}")
            import traceback
            traceback.print_exc()
            
    def load_bots(self):
        """Carga los bots desde base de datos PostgreSQL"""
        if not self.trade_executor or not self.candle_provider:
            print("⚠️ Trade executor y candle provider deben estar configurados antes de cargar bots")
            return
            
        try:
            with get_db() as db:
                bot_models = db.query(BotModel).all()
                
                if not bot_models:
                    print("📂 No hay bots guardados en la base de datos")
                    return
                
                for bot_model in bot_models:
                    strategy = self.strategy_engine.strategies.get(bot_model.strategy_name)
                    if not strategy:
                        print(f"⚠️ Estrategia no encontrada para bot {bot_model.name}: {bot_model.strategy_name}")
                        continue
                    
                    config = BotConfig(
                        name=bot_model.name,
                        strategy_name=bot_model.strategy_name,
                        symbol=bot_model.symbol,
                        timeframe=bot_model.timeframe,
                        trade_amount=bot_model.trade_amount,
                        trade_duration=bot_model.trade_duration,
                        max_daily_loss=bot_model.max_daily_loss,
                        max_daily_trades=bot_model.max_daily_trades,
                        active=bot_model.active,
                        auto_restart=bot_model.auto_restart
                    )
                    
                    bot = TradingBot(
                        bot_id=bot_model.id,
                        config=config,
                        strategy=strategy,
                        trade_executor=self.trade_executor,
                        candle_provider=self.candle_provider,
                        result_checker=self.result_checker,
                        save_callback=self._save_bots,
                        trade_saver=self.save_trade
                    )
                    
                    stat_model = db.query(BotStat).filter(BotStat.bot_id == bot_model.id).first()
                    if stat_model:
                        bot.stats.total_trades = stat_model.total_trades
                        bot.stats.winning_trades = stat_model.winning_trades
                        bot.stats.losing_trades = stat_model.losing_trades
                        bot.stats.total_profit = stat_model.total_profit
                        bot.stats.win_rate = stat_model.win_rate
                        bot.stats.daily_profit = stat_model.daily_profit
                        bot.stats.trades_today = stat_model.trades_today
                        bot.stats.last_trade_time = stat_model.last_trade_time if stat_model.last_trade_time > 0 else None
                        bot.stats.status = stat_model.status
                        bot.stats.error_message = stat_model.error_message
                    
                    bot.gale_level = bot_model.gale_level
                    bot.last_direction = bot_model.last_direction
                    bot.pending_trade = bot_model.pending_trade
                    bot.last_candle_time = bot_model.last_candle_time
                    if bot.gale_level > 0:
                        print(f"🔄 Estado de Gale restaurado: Gale {bot.gale_level}")
                    
                    self.bots[bot_model.id] = bot
                    print(f"📥 Bot cargado: {config.name} ({bot_model.id})")
                
                print(f"✅ {len(self.bots)} bots cargados desde PostgreSQL")
        except Exception as e:
            print(f"❌ Error cargando bots: {e}")
        
    def create_bot(self, config: BotConfig, user_id: str = None) -> str:
        """Crea un nuevo bot de trading para un usuario específico"""
        if not self.trade_executor or not self.candle_provider:
            raise ValueError("Trade executor y candle provider deben estar configurados")
            
        strategy = self.strategy_engine.strategies.get(config.strategy_name)
        if not strategy:
            raise ValueError(f"Estrategia no encontrada: {config.strategy_name}")
            
        bot_id = str(uuid.uuid4())
        
        if config.use_dual_gale:
            if not self.result_checker:
                raise ValueError("Result checker debe estar configurado para bots con dual gale")
            
            from dual_gale_bot import DualGaleBot
            bot = DualGaleBot(
                bot_id=bot_id,
                config=config,
                strategy=strategy,
                trade_executor=self.trade_executor,
                candle_provider=self.candle_provider,
                result_checker=self.result_checker
            )
        else:
            bot = TradingBot(
                bot_id=bot_id,
                config=config,
                strategy=strategy,
                trade_executor=self.trade_executor,
                candle_provider=self.candle_provider,
                result_checker=self.result_checker,
                save_callback=self._save_bots,
                trade_saver=self.save_trade
            )
        
        # Asignar user_id al bot para guardarlo en la BD
        bot.user_id = user_id
        
        self.bots[bot_id] = bot
        self._save_bots()
        
        bot_type = "Dual Gale" if config.use_dual_gale else "Standard"
        print(f"🤖 Bot creado ({bot_type}): {config.name} ({bot_id}) para usuario {user_id}")
        
        return bot_id
        
    def start_bot(self, bot_id: str):
        """Inicia un bot"""
        bot = self.bots.get(bot_id)
        if bot:
            bot.start()
            self._save_bots()
            
    def stop_bot(self, bot_id: str):
        """Detiene un bot"""
        bot = self.bots.get(bot_id)
        if bot:
            bot.stop()
            self._save_bots()
            
    def delete_bot(self, bot_id: str):
        """Elimina un bot"""
        bot = self.bots.get(bot_id)
        if bot:
            bot.stop()
            del self.bots[bot_id]
            self._save_bots()
            print(f"🗑️ Bot eliminado: {bot_id}")
            
    def get_all_bots(self) -> List[dict]:
        """Retorna información de todos los bots"""
        return [
            {
                'config': bot.get_config(),
                'stats': bot.stats.to_dict(),
                'running': bot.running
            }
            for bot in self.bots.values()
        ]
        
    def get_bot_stats(self, bot_id: str) -> Optional[dict]:
        """Retorna estadísticas de un bot específico"""
        bot = self.bots.get(bot_id)
        if bot:
            return bot.stats.to_dict()
        return None


if __name__ == '__main__':
    print("🤖 Auto-Trading Bot - STC Trading System")
    print("Sistema de bots automatizados")
