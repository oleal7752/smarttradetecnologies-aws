"""
Candle Worker - Worker en background que actualiza velas constantemente
Guarda en BD para alta disponibilidad e histórico
SISTEMA MULTI-FUENTE: IQ Option + Twelve Data (mercado real) + Finnhub WebSocket
"""

import threading
import time
from services.candle_service import candle_service
from services.finnhub_service import finnhub_service
from services.twelvedata_service import twelvedata_service
import os

class GlobalAPIWrapper:
    """Wrapper para adaptar IQ_Option API a la interfaz esperada"""
    def __init__(self, api_client):
        self.api = api_client
    
    def get_candles(self, symbol, timeframe, limit):
        """
        Wrapper para get_candles que convierte parámetros al formato IQ Option
        timeframe: 'M1', 'M5', 'M15', 'M30', 'H1', etc.
        """
        # Convertir timeframe a segundos
        timeframe_map = {
            'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800,
            'H1': 3600, 'H4': 14400, 'D1': 86400
        }
        
        timeframe_seconds = timeframe_map.get(timeframe, 300)  # Default M5
        end_time = int(time.time())  # Timestamp actual
        
        # Llamar a la API real
        try:
            raw_candles = self.api.get_candles(symbol, timeframe_seconds, limit, end_time)
            
            # Convertir formato IQ Option al formato interno
            if not raw_candles:
                return []
            
            candles = []
            for c in raw_candles:
                candles.append({
                    'time': int(c['from']),
                    'open': float(c['open']),
                    'high': float(c['max']),
                    'low': float(c['min']),
                    'close': float(c['close']),
                    'volume': float(c.get('volume', 0))
                })
            
            return candles
        except Exception as e:
            print(f"❌ Error obteniendo velas de IQ Option: {e}")
            return []


class CandleWorker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.global_api = None  # API global compartida SOLO para velas
        self.finnhub_active = False  # Estado de Finnhub WebSocket
        self.use_finnhub_fallback = False  # Activar fallback cuando IQ falla
        self.iq_failures = 0  # Contador de fallos de IQ Option
        self.max_iq_failures = 3  # Máximo de fallos antes de activar Finnhub
        self.symbols_to_track = [
            {'symbol': 'EURUSD', 'timeframe': 'M5', 'source': 'twelvedata'},  # Mercado real desde Twelve Data
        ]
        self.update_interval = 5  # segundos entre actualizaciones
        self.twelvedata_api = None  # API de Twelve Data
    
    def connect_global_api(self):
        """
        Conectar UNA VEZ a IQ Option usando credenciales de servicio con timeout
        IMPORTANTE: Esta conexión es SOLO para velas, NO para operaciones
        """
        try:
            # Usar credenciales desde .env SOLO para el worker (temporal)
            email = os.getenv('IQ_EMAIL')
            password = os.getenv('IQ_PASSWORD')
            account_type = os.getenv('IQ_BALANCE_TYPE', 'PRACTICE').upper()
            
            if not email or not password:
                print("❌ No hay credenciales para el worker global de velas")
                print("⚠️  El endpoint devolverá velas desde PostgreSQL si existen")
                return False
            
            print(f"🔗 Conectando worker global de velas a IQ Option...")
            
            # Usar threading para timeout de conexión
            connection_result = {'check': False, 'reason': 'timeout', 'api': None}
            
            def try_connect():
                try:
                    from iqoptionapi.stable_api import IQ_Option
                    api_client = IQ_Option(email, password)
                    check, reason = api_client.connect()
                    connection_result['check'] = check
                    connection_result['reason'] = reason
                    connection_result['api'] = api_client
                except ImportError as e:
                    connection_result['check'] = False
                    connection_result['reason'] = f"iqoptionapi no instalado: {e}"
                    print("❌ iqoptionapi no disponible - usar Finnhub como única fuente")
                except Exception as e:
                    connection_result['check'] = False
                    connection_result['reason'] = str(e)
            
            connect_thread = threading.Thread(target=try_connect)
            connect_thread.start()
            connect_thread.join(timeout=15)  # Timeout de 15 segundos
            
            if connect_thread.is_alive():
                print("❌ Timeout conectando a IQ Option (>15s)")
                print("⚠️  El worker continuará sin conexión - solo velas desde PostgreSQL")
                return False
            
            if connection_result['check']:
                api_client = connection_result['api']
                # Cambiar a cuenta PRACTICE o REAL
                try:
                    # Validar que el tipo de cuenta sea correcto
                    if account_type not in ['PRACTICE', 'REAL']:
                        print(f"⚠️  Tipo de cuenta inválido '{account_type}' - usando PRACTICE por defecto")
                        account_type = 'PRACTICE'
                    
                    api_client.change_balance(account_type)
                    print(f"✅ Worker global de velas conectado a IQ Option ({account_type})")
                except Exception as balance_err:
                    print(f"⚠️  Error cambiando a cuenta {account_type}: {balance_err}")
                    print(f"⚠️  Posible error en IQ_BALANCE_TYPE secret (debe ser 'PRACTICE' o 'REAL')")
                    print("⚠️  Usando cuenta por defecto...")
                
                # Envolver la API con nuestro wrapper
                self.global_api = GlobalAPIWrapper(api_client)
                return True
            else:
                print(f"❌ Error conectando worker global: {connection_result['reason']}")
                return False
                
        except Exception as e:
            print(f"❌ Excepción conectando worker global: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def connect_twelvedata(self):
        """Conectar a Twelve Data API"""
        try:
            print("🔗 Conectando a Twelve Data API...")
            success = twelvedata_service.connect()
            if success:
                self.twelvedata_api = twelvedata_service
                print("✅ Twelve Data API conectada exitosamente")
                return True
            return False
        except Exception as e:
            print(f"❌ Error conectando Twelve Data: {e}")
            return False
    
    def start(self):
        """Iniciar worker en background - solo Twelve Data para velas globales"""
        if self.running:
            print("⚠️  Candle worker ya está activo")
            return
        
        # Conectar SOLO Twelve Data para velas globales de mercado real
        print("🔗 Conectando a Twelve Data para velas globales...")
        twelvedata_success = self.connect_twelvedata()
        
        if not twelvedata_success:
            print("⚠️  Worker iniciado SIN conexión - solo servirá velas desde PostgreSQL")
            print("📝 Las velas no se actualizarán automáticamente")
        else:
            print("✅ Worker conectado a Twelve Data exitosamente")
            print("📊 Twelve Data: Actualizará velas EURUSD (mercado real) cada 5s")
            print("💾 Construyendo historial real de velas para todos los usuarios")
            print("ℹ️  IQ Option: Solo se conecta cuando usuario ingresa credenciales")
        
        self.running = True
        self.thread = threading.Thread(
            target=self.update_loop,
            daemon=True
        )
        self.thread.start()
        print("🚀 Candle worker iniciado - velas globales activas")
    
    def update_loop(self):
        """
        Loop principal de actualización con persistencia inteligente y reconexión automática:
        - Busca última vela en PostgreSQL
        - Si existe, solo carga velas nuevas
        - Si no existe, carga historial inicial de 200 velas
        - Guarda cada vela nueva para construir historial real
        - Si detecta desconexión, reconecta automáticamente
        """
        # Contadores de errores independientes por fuente
        iq_errors = 0
        twelvedata_errors = 0
        max_errors_before_reconnect = 3
        
        while self.running:
            try:
                for config in self.symbols_to_track:
                    symbol = config['symbol']
                    timeframe = config['timeframe']
                    source = config.get('source', 'iqoption')  # Por defecto IQ Option
                    
                    # 1. Buscar última vela guardada en PostgreSQL
                    last_timestamp = candle_service.get_latest_timestamp(symbol, timeframe, source=source)
                    
                    if last_timestamp > 0:
                        # Ya tenemos historial - solo cargar velas nuevas
                        print(f"📊 {symbol} {timeframe} ({source}): Última vela en BD desde {last_timestamp}")
                        limit = 10  # Solo las más recientes
                    else:
                        # Primera vez - cargar historial inicial
                        print(f"🆕 {symbol} {timeframe} ({source}): Inicializando historial...")
                        limit = 200  # Cargar historial completo
                    
                    # 2. Seleccionar API según fuente y verificar conexión
                    api_to_use = None
                    if source == 'twelvedata':
                        if not self.twelvedata_api:
                            print(f"⚠️  Twelve Data no conectado - intentando reconectar...")
                            self.connect_twelvedata()
                        api_to_use = self.twelvedata_api
                    elif source == 'iqoption':
                        if not self.global_api:
                            print(f"⚠️  IQ Option no conectado - intentando reconectar...")
                            self.reconnect()
                        api_to_use = self.global_api
                    
                    if not api_to_use:
                        print(f"⚠️  Sin API disponible para {symbol} {timeframe} (fuente: {source})")
                        continue
                    
                    # 3. Obtener velas desde API y guardar en BD
                    candles = candle_service.update_from_api(
                        api_to_use,
                        symbol,
                        timeframe,
                        limit=limit,
                        source=source
                    )
                    
                    if candles:
                        print(f"✅ {symbol} {timeframe} ({source}): {len(candles)} velas procesadas")
                        # Reset contador de errores para esta fuente
                        if source == 'twelvedata':
                            twelvedata_errors = 0
                        else:
                            iq_errors = 0
                    else:
                        # No se obtuvieron velas - incrementar contador por fuente
                        if source == 'twelvedata':
                            twelvedata_errors += 1
                            print(f"⚠️  Sin velas para {symbol} {timeframe} (Twelve Data) - errores: {twelvedata_errors}")
                            
                            # Reconectar si hay muchos errores
                            if twelvedata_errors >= max_errors_before_reconnect:
                                print(f"🔄 Twelve Data falló {twelvedata_errors} veces - reconectando...")
                                self.connect_twelvedata()
                                twelvedata_errors = 0
                        else:
                            iq_errors += 1
                            print(f"⚠️  Sin velas para {symbol} {timeframe} (IQ Option) - errores: {iq_errors}")
                            
                            # Reconectar si hay muchos errores
                            if iq_errors >= max_errors_before_reconnect:
                                print(f"🔄 IQ Option falló {iq_errors} veces - reconectando...")
                                self.reconnect()
                                iq_errors = 0
                
                # Esperar intervalo (5s por defecto)
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"❌ Error en candle worker: {e}")
                time.sleep(10)
        
        print("🛑 Candle worker detenido")
    
    def on_finnhub_candle(self, candle_data):
        """Callback para velas completadas desde Finnhub WebSocket"""
        try:
            symbol = candle_data['symbol']
            timeframe = candle_data['timeframe']
            
            # Guardar vela en PostgreSQL
            candle_service.save_candle(
                symbol=symbol,
                timeframe=timeframe,
                candle={
                    'time': candle_data['time'],
                    'open': candle_data['open'],
                    'high': candle_data['high'],
                    'low': candle_data['low'],
                    'close': candle_data['close'],
                    'volume': candle_data['volume']
                },
                source='finnhub'
            )
            print(f"📊 Finnhub: Vela guardada {symbol} {timeframe}")
        except Exception as e:
            print(f"❌ Error guardando vela de Finnhub: {e}")
    
    def activate_finnhub_fallback(self):
        """Activar Finnhub WebSocket como backup"""
        if self.finnhub_active:
            print("⚠️  Finnhub WebSocket ya está activo")
            return
        
        try:
            print("🌐 Activando Finnhub WebSocket como backup...")
            success = finnhub_service.start_websocket(on_candle_callback=self.on_finnhub_candle)
            
            if success:
                self.finnhub_active = True
                self.use_finnhub_fallback = True
                print("✅ Finnhub WebSocket activo - velas en tiempo real activadas")
            else:
                print("❌ Error activando Finnhub WebSocket")
        except Exception as e:
            print(f"❌ Error activando Finnhub: {e}")
    
    def deactivate_finnhub_fallback(self):
        """Desactivar Finnhub WebSocket cuando IQ Option se recupere"""
        if not self.finnhub_active:
            return
        
        try:
            print("🔌 Desactivando Finnhub WebSocket - IQ Option recuperado")
            finnhub_service.stop_websocket()
            self.finnhub_active = False
            self.use_finnhub_fallback = False
            print("✅ Finnhub WebSocket desactivado")
        except Exception as e:
            print(f"❌ Error desactivando Finnhub: {e}")
    
    def reconnect(self):
        """Reconectar API global después de desconexión"""
        try:
            print("🔄 Intentando reconectar API global...")
            
            # Cerrar conexión anterior si existe
            if self.global_api and hasattr(self.global_api, 'api'):
                try:
                    self.global_api.api.close()
                except:
                    pass
            
            # Intentar conectar de nuevo
            success = self.connect_global_api()
            
            if success:
                self.iq_failures = 0
                print("✅ Reconexión exitosa - continuando con actualizaciones")
                
                # Si Finnhub está activo, desactivarlo
                if self.finnhub_active:
                    self.deactivate_finnhub_fallback()
            else:
                self.iq_failures += 1
                print(f"❌ Reconexión fallida ({self.iq_failures}/{self.max_iq_failures})")
                
                # Si hay demasiados fallos, activar Finnhub
                if self.iq_failures >= self.max_iq_failures and not self.finnhub_active:
                    print("🚨 IQ Option falló múltiples veces - activando Finnhub...")
                    self.activate_finnhub_fallback()
                
                time.sleep(30)
                
        except Exception as e:
            print(f"❌ Error en reconexión: {e}")
            time.sleep(30)
    
    def stop(self):
        """Detener worker"""
        self.running = False
        if self.global_api:
            try:
                self.global_api.close()
                print("🔌 Desconectada API global de velas")
            except:
                pass
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 Candle worker detenido")
    
    def add_symbol(self, symbol, timeframe):
        """Agregar símbolo para trackear"""
        config = {'symbol': symbol, 'timeframe': timeframe}
        if config not in self.symbols_to_track:
            self.symbols_to_track.append(config)
            print(f"➕ Agregado {symbol} {timeframe} al worker")


# Instancia global
candle_worker = CandleWorker()
