import os
import json
import time
import uuid
import random
from flask import Flask, Blueprint, request, jsonify
import threading
from collections import defaultdict, deque

# Importar candles_store
from candles_store import store_batch, read_last

try:
    from iqoptionapi.stable_api import IQ_Option
    print("✅ IQ Option API importada correctamente")
except ImportError as e:
    print(f"❌ Error importando IQ Option API: {e}")
    print("Instalando iqoptionapi...")
    os.system("pip install iqoptionapi")
    from iqoptionapi.stable_api import IQ_Option

class IQClient:
    def __init__(self):
        self.api = None
        self.connected = False
        self.balance_type = "PRACTICE"
        self.current_balance = 10000.0
        self.email = None
        self.password = None
        
        # Cache mejorado para velas
        self.candles_cache = defaultdict(lambda: deque(maxlen=2000))
        self.last_candle_time = defaultdict(int)
        
        # Cache para balance (evitar llamadas excesivas)
        self.balance_cache = None
        self.balance_cache_time = 0
        self.balance_cache_ttl = 30  # segundos
        
        # Sistema de actualización automática
        self.candles_updater_running = False
        self.symbols_to_watch = ['EURUSD', 'EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC', 'EURJPY-OTC']
        
        # Cola para órdenes
        self.orders_queue = deque()
        self.processing_orders = False
        
        self.load_config()
        print("🚀 IQ Client inicializado")

    def load_config(self):
        """Cargar configuración desde variables de entorno"""
        self.email = os.getenv('IQ_EMAIL', '')
        self.password = os.getenv('IQ_PASSWORD', '')
        self.balance_type = os.getenv('IQ_BALANCE_TYPE', 'PRACTICE')
        
        if not self.email or not self.password:
            print("⚠️  Credenciales no configuradas en .env")

    def connect(self, email=None, password=None, balance_type=None):
        """Conectar a IQ Option con credenciales reales"""
        try:
            if email:
                self.email = email
            if password:
                self.password = password
            if balance_type:
                self.balance_type = balance_type.upper()
                
            if not self.email or not self.password:
                return {"success": False, "error": "Credenciales requeridas"}
            
            print(f"🔌 Conectando a IQ Option como {self.email}...")
            
            # Crear conexión
            self.api = IQ_Option(self.email, self.password)
            
            # Intentar login
            check, reason = self.api.connect()
            
            if check:
                print("✅ Conexión exitosa a IQ Option")
                
                # Cambiar tipo de balance
                if self.balance_type == "REAL":
                    self.api.change_balance("REAL")
                    print("💰 Cambiado a cuenta REAL")
                else:
                    self.api.change_balance("PRACTICE")
                    print("🎯 Cambiado a cuenta PRACTICE")
                
                # Obtener balance real
                balance = self.api.get_balance()
                self.current_balance = balance
                
                self.connected = True
                
                # INICIAR ACTUALIZACIÓN AUTOMÁTICA DE VELAS
                self.start_candles_updater()
                self.start_background_tasks()
                
                return {
                    "success": True, 
                    "balance": balance,
                    "balance_type": self.balance_type,
                    "message": "Conectado exitosamente"
                }
            else:
                print(f"❌ Error de conexión: {reason}")
                return {"success": False, "error": f"Error de login: {reason}"}
                
        except Exception as e:
            print(f"💥 Error conectando: {str(e)}")
            return {"success": False, "error": str(e)}

    def start_candles_updater(self):
        """Iniciar actualización automática de velas cada 2 segundos"""
        if self.candles_updater_running:
            return
            
        self.candles_updater_running = True
        
        def updater():
            while self.candles_updater_running and self.connected:
                try:
                    for symbol in self.symbols_to_watch:
                        self.update_candles_for_symbol(symbol)
                    time.sleep(2)  # Actualizar cada 2 segundos
                except Exception as e:
                    print(f"Error en actualizador de velas: {e}")
                    time.sleep(5)
        
        threading.Thread(target=updater, daemon=True).start()
        print("🔄 Iniciado actualizador automático de velas")

    def update_candles_for_symbol(self, symbol, timeframe="M5", limit=200):
        """Actualizar velas para un símbolo específico"""
        if not self.connected:
            return
            
        try:
            # Obtener velas actualizadas
            tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}
            minutes = tf_map.get(timeframe, 5)
            
            candles = self.api.get_candles(symbol, minutes * 60, limit, time.time())
            
            if candles and len(candles) > 0:
                # Formatear todas las velas
                all_candles = []
                for candle in candles:
                    candle_time = int(candle["from"])
                    formatted_candle = {
                        "time": candle_time,
                        "open": float(candle["open"]),
                        "high": float(candle["max"]),
                        "low": float(candle["min"]),
                        "close": float(candle["close"]),
                        "volume": int(candle.get("volume", 0))
                    }
                    all_candles.append(formatted_candle)
                
                if all_candles:
                    # Reemplazar cache completo con datos actualizados
                    self.candles_cache[symbol] = deque(all_candles, maxlen=limit)
                    self.last_candle_time[symbol] = all_candles[-1]["time"]
                
        except Exception as e:
            print(f"Error actualizando velas para {symbol}: {e}")

    def get_candles(self, symbol, timeframe="M5", limit=200):
        """Obtener velas del cache"""
        try:
            # Si hay velas en cache, devolverlas
            if symbol in self.candles_cache and len(self.candles_cache[symbol]) > 0:
                candles = list(self.candles_cache[symbol])[-limit:]
                print(f"📈 Devolviendo {len(candles)} velas desde cache para {symbol}")
                return candles
            else:
                # Si no hay cache, obtener del API
                print(f"🔄 Cache vacío, obteniendo velas iniciales para {symbol}")
                return self.get_initial_candles(symbol, timeframe, limit)
                
        except Exception as e:
            print(f"Error obteniendo velas: {e}")
            return self.generate_demo_candles(symbol, limit)

    def get_initial_candles(self, symbol, timeframe="M5", limit=200):
        """Obtener velas iniciales del API"""
        if not self.connected:
            return self.generate_demo_candles(symbol, limit)
            
        try:
            tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}
            minutes = tf_map.get(timeframe, 5)
            
            candles = self.api.get_candles(symbol, minutes * 60, limit, time.time())
            
            if candles:
                formatted_candles = []
                for candle in candles:
                    # IQ Option devuelve timestamp en segundos Unix
                    candle_time = int(candle["from"])
                    formatted_candle = {
                        "time": candle_time,
                        "open": float(candle["open"]),
                        "high": float(candle["max"]),
                        "low": float(candle["min"]),
                        "close": float(candle["close"]),
                        "volume": int(candle.get("volume", 0))
                    }
                    formatted_candles.append(formatted_candle)
                    self.last_candle_time[symbol] = candle_time
                
                # Ordenar y guardar en cache
                formatted_candles.sort(key=lambda x: x["time"])
                self.candles_cache[symbol].extend(formatted_candles)
                
                # Guardar en CSV
                store_batch(symbol, timeframe, formatted_candles)
                
                print(f"📊 Obtenidas {len(formatted_candles)} velas iniciales de {symbol}")
                return formatted_candles
            else:
                return self.generate_demo_candles(symbol, limit)
                
        except Exception as e:
            print(f"Error obteniendo velas iniciales: {e}")
            return self.generate_demo_candles(symbol, limit)

    def generate_demo_candles(self, symbol, limit=200):
        """Generar velas demo para desarrollo"""
        print(f"🎭 Generando {limit} velas demo para {symbol}")
        
        candles = []
        base_price = 1.08500 if 'EUR' in symbol else 1.25000 if 'GBP' in symbol else 150.00
        current_time = int(time.time())  # Usar segundos, no milisegundos
        
        for i in range(limit):
            variation = random.uniform(-0.001, 0.001)
            open_price = base_price + variation
            close_price = open_price + random.uniform(-0.0005, 0.0005)
            high_price = max(open_price, close_price) + random.uniform(0, 0.0003)
            low_price = min(open_price, close_price) - random.uniform(0, 0.0003)
            
            candle = {
                "time": current_time - (limit - i - 1) * 5 * 60,  # Usar segundos
                "open": round(open_price, 5),
                "high": round(high_price, 5),
                "low": round(low_price, 5),
                "close": round(close_price, 5),
                "volume": random.randint(100, 1000)
            }
            
            candles.append(candle)
            base_price = close_price
        
        return candles

    def get_available_symbols(self):
        """Obtener todos los símbolos disponibles desde IQ Option API o fallback"""
        
        # Lista hardcoded como fallback
        fallback_symbols = {
            "success": True,
            "symbols": {
                "OTC": [
                    {"name": "EURUSD-OTC", "display": "EUR/USD (OTC)"},
                    {"name": "GBPUSD-OTC", "display": "GBP/USD (OTC)"},
                    {"name": "USDJPY-OTC", "display": "USD/JPY (OTC)"},
                    {"name": "AUDUSD-OTC", "display": "AUD/USD (OTC)"},
                    {"name": "USDCAD-OTC", "display": "USD/CAD (OTC)"},
                    {"name": "NZDUSD-OTC", "display": "NZD/USD (OTC)"},
                    {"name": "EURGBP-OTC", "display": "EUR/GBP (OTC)"},
                    {"name": "EURJPY-OTC", "display": "EUR/JPY (OTC)"},
                    {"name": "GBPJPY-OTC", "display": "GBP/JPY (OTC)"},
                    {"name": "AUDJPY-OTC", "display": "AUD/JPY (OTC)"},
                    {"name": "EURAUD-OTC", "display": "EUR/AUD (OTC)"},
                    {"name": "GBPAUD-OTC", "display": "GBP/AUD (OTC)"}
                ],
                "REAL": [
                    {"name": "EURUSD", "display": "EUR/USD"},
                    {"name": "GBPUSD", "display": "GBP/USD"},
                    {"name": "USDJPY", "display": "USD/JPY"},
                    {"name": "AUDUSD", "display": "AUD/USD"},
                    {"name": "USDCAD", "display": "USD/CAD"},
                    {"name": "NZDUSD", "display": "NZD/USD"},
                    {"name": "EURGBP", "display": "EUR/GBP"},
                    {"name": "EURJPY", "display": "EUR/JPY"},
                    {"name": "GBPJPY", "display": "GBP/JPY"},
                    {"name": "AUDJPY", "display": "AUD/JPY"}
                ]
            }
        }
        
        if not self.connected:
            print("⚠️  No conectado a IQ Option, usando pares predefinidos")
            return fallback_symbols
        
        # Intentar obtener de la API con timeout
        try:
            print("🔍 Obteniendo símbolos disponibles desde IQ Option...")
            
            # Esta llamada puede tardar, si falla usamos fallback
            all_assets = self.api.get_all_open_time()
            
            if not all_assets or not isinstance(all_assets, dict):
                print("⚠️  No se pudieron obtener símbolos de API, usando fallback")
                return fallback_symbols
            
            symbols_otc = []
            symbols_real = []
            
            # Extraer solo forex que es lo más usado
            forex_assets = all_assets.get("forex", {})
            for asset_key, asset_info in forex_assets.items():
                asset_name = str(asset_key) if not isinstance(asset_key, str) else asset_key
                
                if not asset_name:
                    continue
                
                is_otc = asset_name.endswith("-OTC")
                display_name = asset_name.replace("-OTC", " (OTC)") if is_otc else asset_name
                display_name = display_name.replace("USD", "/USD").replace("EUR", "EUR/").replace("GBP", "GBP/").replace("JPY", "/JPY").replace("AUD", "AUD/").replace("CAD", "/CAD").replace("NZD", "NZD/")
                
                symbol_data = {
                    "name": asset_name,
                    "display": display_name
                }
                
                if is_otc:
                    symbols_otc.append(symbol_data)
                else:
                    symbols_real.append(symbol_data)
            
            if not symbols_otc and not symbols_real:
                print("⚠️  No se encontraron símbolos, usando fallback")
                return fallback_symbols
            
            print(f"✅ Obtenidos {len(symbols_otc)} pares OTC y {len(symbols_real)} pares reales")
            
            return {
                "success": True,
                "symbols": {
                    "OTC": symbols_otc,
                    "REAL": symbols_real
                }
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo símbolos: {e}, usando fallback")
            return fallback_symbols

    def start_background_tasks(self):
        """Iniciar tareas en segundo plano"""
        if not self.processing_orders:
            self.processing_orders = True
            threading.Thread(target=self.process_orders_queue, daemon=True).start()
            print("🔄 Iniciado procesador de órdenes")

    def process_orders_queue(self):
        """Procesar cola de órdenes"""
        while self.processing_orders:
            try:
                if self.orders_queue and self.connected:
                    order_data = self.orders_queue.popleft()
                    result = self.place_real_order(**order_data)
                    print(f"Orden procesada: {result}")
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error procesando órdenes: {e}")
                time.sleep(1)

    def get_real_balance(self):
        """Obtener balance real actual (con cache)"""
        if not self.connected:
            return {"error": "No conectado", "balance": 0}
        
        # Usar cache si es reciente
        current_time = time.time()
        if self.balance_cache and (current_time - self.balance_cache_time) < self.balance_cache_ttl:
            return self.balance_cache
        
        # Cache expirado o no existe, obtener balance fresco con timeout
        try:
            # Verificar estado de la conexión WebSocket antes de intentar
            if not hasattr(self.api, 'websocket_client') or not self.api.websocket_client:
                raise Exception("WebSocket no conectado")
            
            # Intentar obtener balance con protección
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Balance timeout")
            
            # Configurar timeout de 3 segundos
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(3)
            
            try:
                balance = self.api.get_balance()
                signal.alarm(0)  # Cancelar alarma
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            
            self.current_balance = balance
            
            # Actualizar cache
            self.balance_cache = {
                "balance": balance,
                "balance_type": self.balance_type,
                "currency": "USD"
            }
            self.balance_cache_time = current_time
            
            return self.balance_cache
        except (TimeoutError, Exception) as e:
            print(f"Error obteniendo balance: {e}")
            # Si hay cache antiguo, devolverlo en caso de error
            if self.balance_cache:
                return self.balance_cache
            return {"error": "Balance temporalmente no disponible", "balance": 0}

    def place_real_order(self, symbol, direction, amount, duration=1):
        """Enviar orden real a IQ Option"""
        if not self.connected:
            return {"success": False, "error": "No conectado a IQ Option"}
        
        try:
            print(f"📈 Enviando orden: {direction} {symbol} ${amount} por {duration}min")
            
            action = "call" if direction.upper() == "CALL" else "put"
            response = self.api.buy(amount, symbol, action, duration)
            
            # IQ Option devuelve una tupla (success, order_id)
            if isinstance(response, tuple) and len(response) == 2:
                success, order_id = response
                if success and order_id:
                    print(f"✅ Orden enviada exitosamente. ID: {order_id}")
                    return {
                        "success": True,
                        "order_id": str(order_id),
                        "symbol": symbol,
                        "direction": direction,
                        "amount": amount,
                        "duration": duration,
                        "message": f"Orden ejecutada. ID: {order_id}"
                    }
                else:
                    print(f"❌ Orden rechazada por IQ Option: {response}")
                    return {"success": False, "error": f"Orden rechazada: {order_id}"}
            
            # Si devuelve solo el ID (versiones antiguas de la API)
            elif response and str(response).isdigit():
                print(f"✅ Orden enviada. ID: {response}")
                return {
                    "success": True,
                    "order_id": str(response),
                    "symbol": symbol,
                    "direction": direction,
                    "amount": amount,
                    "duration": duration,
                    "message": f"Orden ejecutada. ID: {response}"
                }
            else:
                print(f"❌ Respuesta inesperada de IQ Option: {response}")
                return {"success": False, "error": f"Respuesta inesperada: {response}"}
                
        except Exception as e:
            print(f"💥 Error ejecutando orden: {str(e)}")
            return {"success": False, "error": str(e)}

# Instancia global
iq_client = IQClient()

# Flask app
app = Flask(__name__)

# Configurar CORS para permitir requests del dashboard
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Registrar blueprints de bots y estrategias
try:
    from bot_routes import bot_bp
    app.register_blueprint(bot_bp)
    print("✅ Bot routes registradas")
except Exception as e:
    print(f"⚠️ Error registrando bot routes: {e}")

@app.route('/api/iq/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "JSON requerido"}), 400
    
    email = data.get('email')
    password = data.get('password')
    balance_type = data.get('balance_type', 'PRACTICE')
    
    result = iq_client.connect(email, password, balance_type)
    return jsonify(result)

@app.route('/api/iq/balance', methods=['GET'])
def get_balance():
    """
    Endpoint V1 (legacy) con soporte multi-usuario
    - Si hay user_id en sesión → usa AccountManager (cuenta individual)
    - Si no hay user_id → fallback a iq_client global
    """
    from flask import session
    
    user_id = session.get('user_id')
    
    try:
        from services.service_manager import service_manager
        
        if user_id:
            broker = request.args.get('broker', 'iqoption')
            account = service_manager.account_manager.get_account(user_id, broker)
            
            if account and account.connected:
                balance = account.get_balance()
                return jsonify({
                    "balance": balance,
                    "balance_type": account.account_type if hasattr(account, 'account_type') else 'PRACTICE',
                    "currency": "USD",
                    "user_id": user_id,
                    "source": "user_account"
                })
    except Exception as e:
        print(f"⚠️ Error obteniendo balance de usuario: {e}")
    
    result = iq_client.get_real_balance()
    if 'source' not in result:
        result['source'] = 'global_account'
    return jsonify(result)

@app.route('/api/iq/candles', methods=['GET'])
def get_candles():
    # Verificar acceso: usuario debe tener sesión Y (suscripción activa O código promocional válido)
    if 'user_id' not in session:
        print("❌ ACCESO DENEGADO: Sin sesión al intentar acceder a velas")
        return jsonify({'success': False, 'error': 'No autorizado. Inicia sesión primero.'}), 401
    
    user_id = session['user_id']
    print(f"🔐 Verificando acceso a velas para user_id: {user_id}")
    
    from database import Subscription, PromoCode, SubscriptionStatus, get_db
    with get_db() as db:
        # Verificar suscripción activa
        has_subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > datetime.utcnow()
        ).first() is not None
        
        # Verificar código promocional activo
        has_promo = db.query(PromoCode).filter(
            PromoCode.assigned_to == user_id,
            PromoCode.is_used == True,
            PromoCode.is_active == True,
            PromoCode.expires_at > datetime.utcnow()
        ).first() is not None
        
        if not has_subscription and not has_promo:
            print(f"❌ ACCESO DENEGADO A VELAS: Usuario {user_id} sin plan ni código activo")
            return jsonify({
                'success': False,
                'error': 'Acceso denegado. Necesitas una suscripción activa o código promocional válido.',
                'requires_subscription': True
            }), 403
    
    print(f"✅ ACCESO A VELAS PERMITIDO: Usuario {user_id}")
    
    symbol = request.args.get('symbol', 'EURUSD-OTC')
    timeframe = request.args.get('timeframe', 'M5')
    limit = int(request.args.get('limit', 200))
    
    candles = iq_client.get_candles(symbol, timeframe, limit)
    return jsonify(candles)

@app.route('/api/iq/symbols', methods=['GET'])
def get_symbols():
    """Obtener todos los símbolos disponibles desde IQ Option"""
    result = iq_client.get_available_symbols()
    return jsonify(result)

@app.route('/api/iq/trade', methods=['POST'])
def place_trade():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "JSON requerido"}), 400
    
    symbol = data.get('symbol', 'EURUSD-OTC')
    direction = data.get('direction', 'CALL')
    amount = float(data.get('amount', 1))
    duration = int(data.get('duration', 1))
    
    # VALIDACIÓN CRÍTICA: Verificar que el símbolo existe en IQ Option real
    if not iq_client.connected:
        return jsonify({
            "success": False, 
            "error": "No conectado a IQ Option. No se pueden ejecutar órdenes reales."
        }), 400
    
    # Verificar símbolos disponibles
    available_symbols = iq_client.get_available_symbols()
    if available_symbols and available_symbols.get('success'):
        all_symbols = []
        for category in available_symbols.get('symbols', {}).values():
            all_symbols.extend([s['name'] for s in category])
        
        if symbol not in all_symbols:
            return jsonify({
                "success": False,
                "error": f"⚠️ Símbolo '{symbol}' NO disponible en IQ Option. No se puede ejecutar orden real."
            }), 400
    
    result = iq_client.place_real_order(symbol, direction, amount, duration)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "connected": iq_client.connected,
        "balance_type": iq_client.balance_type,
        "candles_updater": iq_client.candles_updater_running
    })

# ============================================================
# NUEVAS RUTAS MULTI-USUARIO CON SERVICIOS
# ============================================================

try:
    from services.service_manager import service_manager
    
    @app.route('/api/v2/candles', methods=['GET'])
    def get_candles_v2():
        """Obtener velas desde BD (alta disponibilidad)"""
        symbol = request.args.get('symbol', 'EURUSD-OTC')
        timeframe = request.args.get('timeframe', 'M5')
        limit = int(request.args.get('limit', 200))
        
        candles = service_manager.get_candles(symbol, timeframe, limit)
        return jsonify(candles)
    
    @app.route('/api/v2/symbols', methods=['GET'])
    def get_symbols_v2():
        """Obtener símbolos desde cache compartido"""
        symbols = service_manager.get_symbols(iq_client)
        return jsonify(symbols)
    
    @app.route('/api/v2/user/balance', methods=['GET'])
    def get_user_balance_v2():
        """Obtener balance de la cuenta del usuario autenticado"""
        from flask import session
        
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                "error": "Usuario no autenticado",
                "balance": 0,
                "broker_connected": False
            }), 401
        
        broker = request.args.get('broker', 'iqoption')
        
        account = service_manager.account_manager.get_account(user_id, broker)
        
        if not account or not account.connected:
            return jsonify({
                "error": "Broker no conectado. Conecta tu cuenta primero.",
                "balance": 0,
                "broker_connected": False,
                "user_id": user_id
            }), 409
        
        try:
            balance = account.get_balance()
            return jsonify({
                "success": True,
                "balance": balance,
                "broker_connected": True,
                "user_id": user_id,
                "broker": broker,
                "account_type": account.account_type if hasattr(account, 'account_type') else 'PRACTICE'
            })
        except Exception as e:
            return jsonify({
                "error": f"Error obteniendo balance: {str(e)}",
                "balance": 0,
                "broker_connected": False
            }), 500
    
    @app.route('/api/v2/user/account', methods=['POST'])
    def connect_user_account():
        """Conectar cuenta de usuario específico"""
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "JSON requerido"}), 400
        
        user_id = data.get('user_id')
        broker = data.get('broker', 'iqoption')
        
        if not user_id:
            return jsonify({"error": "user_id requerido"}), 400
        
        account = service_manager.get_user_account(user_id, broker)
        
        if account and account.connected:
            return jsonify({
                "success": True,
                "user_id": user_id,
                "broker": broker,
                "balance": account.get_balance(),
                "account_type": account.account_type if hasattr(account, 'account_type') else 'PRACTICE'
            })
        
        return jsonify({"success": False, "error": "No se pudo conectar"}), 400
    
    @app.route('/api/v2/user/trade', methods=['POST'])
    def place_user_trade():
        """Ejecutar trade en la cuenta del usuario"""
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "JSON requerido"}), 400
        
        user_id = data.get('user_id')
        broker = data.get('broker', 'iqoption')
        symbol = data.get('symbol', 'EURUSD-OTC')
        direction = data.get('direction', 'CALL')
        amount = float(data.get('amount', 1))
        duration = int(data.get('duration', 1))
        
        if not user_id:
            return jsonify({"error": "user_id requerido"}), 400
        
        # VALIDACIÓN: Verificar símbolos disponibles en broker real
        if broker == 'iqoption':
            available_symbols = service_manager.get_symbols(iq_client)
            if available_symbols and available_symbols.get('success'):
                all_symbols = []
                for category in available_symbols.get('symbols', {}).values():
                    all_symbols.extend([s['name'] for s in category])
                
                if symbol not in all_symbols:
                    return jsonify({
                        "success": False,
                        "error": f"⚠️ Símbolo '{symbol}' NO disponible en {broker}. No se puede ejecutar orden real."
                    }), 400
        
        account = service_manager.get_user_account(user_id, broker)
        
        if not account or not account.connected:
            return jsonify({"success": False, "error": "Usuario no conectado"}), 400
        
        result = account.place_order(symbol, direction, amount, duration)
        return jsonify(result)
    
    @app.route('/api/v2/user/disconnect', methods=['POST'])
    def disconnect_user():
        """Desconectar usuario"""
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "JSON requerido"}), 400
        
        user_id = data.get('user_id')
        broker = data.get('broker', 'iqoption')
        
        if not user_id:
            return jsonify({"error": "user_id requerido"}), 400
        
        service_manager.disconnect_user(user_id, broker)
        return jsonify({"success": True})
    
    print("✅ Rutas multi-usuario v2 registradas")
    
except Exception as e:
    print(f"⚠️  Servicios multi-usuario no disponibles: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando IQ Client con actualización automática de velas...")
    
    # Función para conectar en background
    def connect_in_background():
        time.sleep(2)  # Esperar que el servidor inicie
        email = os.getenv('IQ_EMAIL')
        password = os.getenv('IQ_PASSWORD')
        balance_type = os.getenv('IQ_BALANCE_TYPE', 'PRACTICE')
        
        if email and password:
            print(f"🔐 Conectando automáticamente con: {email}")
            connection_result = iq_client.connect(email, password, balance_type)
            if connection_result.get('success'):
                print(f"✅ Conectado exitosamente a IQ Option")
                print(f"💰 Balance: ${connection_result.get('balance')}")
                print(f"📊 Modo: {connection_result.get('balance_type')}")
                
                # Inicializar servicios multi-usuario
                try:
                    service_manager.initialize()
                    # Iniciar worker de velas en background
                    service_manager.start_candle_worker(iq_client)
                    print("✅ Servicios multi-usuario iniciados")
                except Exception as e:
                    print(f"⚠️  Error iniciando servicios: {e}")
            else:
                print(f"⚠️  Error de conexión: {connection_result.get('error')}")
                print("⚠️  El sistema funcionará con datos demo")
        else:
            print("⚠️  Credenciales no configuradas en Secrets")
            print("⚠️  El sistema funcionará con datos demo")
    
    # Iniciar conexión en thread separado
    connection_thread = threading.Thread(target=connect_in_background, daemon=True)
    connection_thread.start()
    
    # Iniciar servidor Flask inmediatamente
    app.run(host="0.0.0.0", port=5002, debug=True, use_reloader=False)