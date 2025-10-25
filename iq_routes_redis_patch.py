#!/usr/bin/env python3
"""
iq_routes_redis_patch.py - IQ API (puerto 5002)
- Encola logins y órdenes en Redis
- Endpoint de velas mock
- CORS habilitado para que el dashboard en 5001 pueda consumir esta API
"""

from flask import request, jsonify
from candles_store import store_batch, read_last

import os, json, time, uuid, random
from datetime import datetime
from flask import Flask, Blueprint, request, jsonify, session
import threading
from collections import defaultdict, deque
from auth_routes import requires_active_access

# --- NUEVOS ENDPOINTS V2, libres de conflicto con rutas antiguas ---

from flask import request, jsonify
from candles_store import store_batch, read_last

# @app.post("/api/iq/candles_v2")
def post_candles_v2():
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "JSON requerido"}), 400

    if isinstance(data, dict) and "candles" in data:
        candles = data["candles"]
    elif isinstance(data, list):
        candles = data
    elif isinstance(data, dict):
        candles = [data]
    else:
        candles = []

    symbol = request.args.get("symbol")
    timeframe = (request.args.get("timeframe") or "M5").upper()

    if not symbol and candles and isinstance(candles[0], dict):
        symbol = candles[0].get("symbol")

    if not symbol:
        return jsonify({"error": "symbol requerido (query ?symbol=... o dentro de cada vela)"}), 400

    info = store_batch(symbol, timeframe, candles)
    return jsonify({"status": "ok", "saved": info["inserted"], "size": info["size"], "csv_written": info["csv_written"]})

# @app.get("/api/iq/candles_v2")
def get_candles_v2():
    symbol = request.args.get("symbol")
    tf = (request.args.get("timeframe") or "M5").upper()
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200

    if not symbol:
        return jsonify({"error": "symbol requerido"}), 400

    arr = read_last(symbol, tf, limit=limit)
    # Para distinguir que estás en la ruta nueva, puedes añadir meta si quieres:
    # return jsonify({"source":"v2","data":arr})
    return jsonify(arr)

# Cache en memoria que simula Redis
class MemoryRedis:
    def __init__(self):
        self.data = {}
        self.lists = defaultdict(deque)
        self.lock = threading.Lock()
        self.candles_data = {}
        self.symbols_data = []
        self.balance_data = {"balance": 10000.0, "currency": "USD"}
        print("[MemoryRedis] Inicializado - Cache en memoria")


    def setex(self, key, time, value):
        """Simula SETEX de Redis: guarda con expiración en segundos"""
        self.set(key, value)
        print(f"[MemoryRedis] SETEX {key} = {value} (TTL: {time}s)")

    
    def get(self, key):
        with self.lock:
            return self.data.get(key)
    
    def set(self, key, value):
        with self.lock:
            self.data[key] = value
    
    def lpush(self, key, value):
        with self.lock:
            self.lists[key].appendleft(value)
    
    def rpush(self, key, value):
        with self.lock:
            self.lists[key].append(value)
    
    def lpop(self, key):
        with self.lock:
            try:
                return self.lists[key].popleft()
            except IndexError:
                return None
    
    def llen(self, key):
        with self.lock:
            return len(self.lists[key])
    
    def delete(self, *keys):
        """Elimina una o más claves del cache"""
        with self.lock:
            count = 0
            for key in keys:
                if key in self.data:
                    del self.data[key]
                    count += 1
                if key in self.lists:
                    del self.lists[key]
                    count += 1
            return count

try:
    # CORS es opcional pero recomendado cuando el dashboard está en 5001
    from flask_cors import CORS
    USE_CORS = True
except Exception:
    USE_CORS = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Añadir soporte para CORS solo si está disponible
if USE_CORS:
    CORS(app, 
         resources={r"/*": {"origins": "*"}}, 
         allow_headers=["Content-Type", "Accept", "Authorization", "Access-Control-Allow-Origin"],
         methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])
else:
    # CORS manual si no está disponible flask-cors
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

# Usar cache en memoria en lugar de Redis
r = MemoryRedis()

from bot_routes import bot_bp, init_bot_system

bp = Blueprint("iq", __name__, url_prefix="/api/iq")

@bp.route("/login", methods=["GET", "POST"])
def iq_login():
    if request.method == "GET":
        # GET request - retornar información del endpoint
        return jsonify({
            "endpoint": "/api/iq/login",
            "method": "POST",
            "description": "IQ Option login endpoint",
            "required_fields": ["email", "password"],
            "optional_fields": ["balance_type"],
            "example": {
                "email": "user@example.com",
                "password": "your_password",
                "balance_type": "PRACTICE"
            }
        })
    
    # POST request - procesar login
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    balance = data.get("balance_type") or "PRACTICE"
    
    if not email or not password:
        return jsonify(error="missing credentials"), 400

    payload = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password": password,
        "balance": balance,
        "created_at": int(time.time())
    }
    r.rpush("logins", json.dumps(payload))
    
    # Guardar sesión activa en Redis
    session_key = "iq_active_session"
    session_data = {
        "login_id": payload["id"],
        "email": email,
        "balance_type": balance,
        "logged_in_at": int(time.time()),
        "status": "active"
    }
    r.setex(session_key, 7200, json.dumps(session_data))  # 2 horas
    
    return jsonify(ok=True, queued=True, id=payload["id"], session=session_data)

@bp.route("/logout", methods=["POST"])
def iq_logout():
    """Logout de IQ Option"""
    try:
        # Limpiar sesión activa
        session_key = "iq_active_session"
        r.delete(session_key)
        
        # Encolar comando de logout para el cliente
        logout_payload = {
            "id": str(uuid.uuid4()),
            "action": "logout",
            "created_at": int(time.time())
        }
        r.rpush("logouts", json.dumps(logout_payload))
        
        return jsonify({
            "ok": True,
            "message": "Logout successful",
            "logout_id": logout_payload["id"]
        })
        
    except Exception as e:
        return jsonify({"error": f"Error en logout: {str(e)}"}), 500

@bp.route("/session", methods=["GET"])
def iq_session():
    """Obtener información de sesión activa"""
    try:
        session_key = "iq_active_session"
        session_data = r.get(session_key)
        
        if session_data:
            try:
                session_info = json.loads(session_data)
                return jsonify({
                    "active": True,
                    "session": session_info
                })
            except json.JSONDecodeError:
                pass
        
        return jsonify({
            "active": False,
            "message": "No active session"
        })
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo sesión: {str(e)}"}), 500

@bp.route("/order", methods=["POST"])
def iq_order():
    data = request.get_json(force=True, silent=True) or {}
    sym = data.get("symbol")
    act = data.get("action")
    if not sym or not act:
        return jsonify(error="missing fields"), 400
    payload = {
        "id": str(uuid.uuid4()),
        "symbol": sym,
        "action": act,
        "amount": float(data.get("amount", 5)),
        "option_type": data.get("option_type", "binary"),
        "duration": int(data.get("duration", 5)),
        "created_at": int(time.time())
    }
    r.rpush("orders", json.dumps(payload))
    return jsonify(ok=True, order_id=payload["id"], type=payload["option_type"])

@bp.route("/trade", methods=["POST", "OPTIONS"])
def iq_trade_alias():
    """
    Ejecutar órdenes CALL/PUT - SOLO si el usuario tiene cuenta conectada
    NO usa credenciales del .env - cada usuario debe conectar con sus propias credenciales
    """
    if request.method == "OPTIONS":
        return jsonify(ok=True)
        
    try:
        data = request.get_json(force=True, silent=True) or {}
        
        # Mapear nombres de campos del dashboard
        if "direction" in data:
            data["action"] = data["direction"].lower()
        if "symbol" in data:
            data["asset"] = data["symbol"]
        if "expiration" in data:
            data["duration"] = data["expiration"]
            
        # Validar parámetros
        asset = data.get("asset")
        if not asset:
            return jsonify(success=False, message="Símbolo requerido"), 400
        asset = asset.upper()
            
        act = data.get("action", "call").lower()
        if act not in ["call", "put"]:
            return jsonify(success=False, message=f"Acción inválida: {act}"), 400

        amount = float(data.get("amount", 1))
        duration = int(data.get("duration", 1))
        
        # Buscar cuenta conectada EXPLÍCITAMENTE por el usuario
        # NO usar credenciales del .env
        print(f"🔍 Buscando cuenta conectada para ejecutar {act.upper()} en {asset}")
        
        account_keys = [k for k in r.data.keys() if k.startswith("iq_account_")]
        print(f"🔍 Cuentas disponibles: {account_keys}")
        
        for key in account_keys:
            account = r.data[key]
            if account.connected and account.api:
                # Enviar símbolo exacto (sin modificarlo) a IQ Option API
                result = account.place_order(asset, act, amount, duration)
                if result.get("success"):
                    print(f"✅ Orden {act.upper()} ejecutada: {asset}, ${amount}, {duration}min")
                    return jsonify({
                        "success": True,
                        "message": f"Orden {act.upper()} ejecutada exitosamente",
                        "order_id": result.get("order_id"),
                        "asset": asset,
                        "amount": amount,
                        "duration": duration
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": result.get("error", "Error ejecutando orden")
                    }), 400
        
        # Si no hay cuenta conectada, devolver ERROR (no modo mock)
        print(f"❌ No hay cuenta conectada - rechazando orden {act.upper()} en {asset}")
        return jsonify({
            "success": False,
            "message": "Debes conectar tu cuenta de IQ Option antes de operar",
            "error": "NO_ACCOUNT_CONNECTED"
        }), 403
        
    except Exception as e:
        print(f"❌ Error procesando trade: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(success=False, message=f"Error procesando trade: {str(e)}"), 500

@bp.route("/order_results", methods=["GET"])
def iq_order_results():
    """Endpoint para obtener resultados de órdenes ejecutadas"""
    try:
        # Obtener todos los resultados
        results = []
        while True:
            result_data = r.lpop("order_results")
            if not result_data:
                break
            try:
                result = json.loads(result_data)
                results.append(result)
            except json.JSONDecodeError:
                continue
        
        return jsonify({
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo resultados: {str(e)}"}), 500

@bp.route("/symbols", methods=["GET"])
def iq_symbols():
    """Endpoint para obtener símbolos disponibles desde IQ Option"""
    try:
        # Intentar obtener símbolos desde el candle worker (conexión global)
        from services.candle_worker import candle_worker
        
        api_connection = None
        
        # Prioridad 1: Usar API del candle worker global
        if candle_worker and candle_worker.global_api and hasattr(candle_worker.global_api, 'api'):
            api_connection = candle_worker.global_api.api
            print("🔍 Usando conexión del candle worker para obtener símbolos...")
        
        # Prioridad 2: Buscar cuenta conectada en el account manager
        if not api_connection:
            from services.account_manager import account_manager
            for account_key, account in account_manager.accounts.items():
                if account.connected and hasattr(account, 'api'):
                    api_connection = account.api
                    print("🔍 Usando conexión de cuenta de usuario para obtener símbolos...")
                    break
        
        if api_connection:
            try:
                # Método 1: Intentar get_all_open_time (puede fallar con KeyError 'underlying')
                try:
                    actives = api_connection.get_all_open_time()
                except (KeyError, AttributeError) as e:
                    print(f"⚠️ get_all_open_time falló: {e}, usando get_all_init_v2...")
                    # Método 2: Usar get_all_init_v2 que devuelve datos de inicialización
                    init_data = api_connection.get_all_init_v2()
                    # get_all_init_v2 devuelve: {binary: {actives: {id: {...}}, list: []}}
                    if isinstance(init_data, dict) and "binary" in init_data:
                        binary_data = init_data["binary"]
                        # Los activos están en binary['actives']
                        if isinstance(binary_data, dict) and "actives" in binary_data:
                            actives = {"binary": binary_data["actives"]}
                        else:
                            actives = {"binary": binary_data}
                    else:
                        actives = {}
                
                if actives and 'binary' in actives:
                    symbols_list = []
                    binary_actives = actives['binary']
                    
                    # Procesar símbolos binarios (puede ser dict con IDs o dict con símbolos)
                    if isinstance(binary_actives, dict):
                        # Formato dict: {id_or_symbol: {name: ..., enabled: ..., ...}}
                        for key, info in binary_actives.items():
                            if isinstance(info, dict):
                                # Extraer el símbolo del campo 'name' (formato: 'front.SYMBOL-OTC')
                                symbol_name = info.get('name', key)
                                if symbol_name.startswith('front.'):
                                    symbol = symbol_name.replace('front.', '')
                                else:
                                    symbol = symbol_name
                                
                                is_open = info.get('enabled', info.get('open', False))
                                if symbol:
                                    symbols_list.append({
                                        "symbol": symbol,
                                        "displayName": symbol.replace('-OTC', ' (OTC)'),
                                        "active": is_open,
                                        "category": "forex"
                                    })
                    elif isinstance(binary_actives, list):
                        # Formato list: [{id: symbol, enabled: bool, ...}]
                        for item in binary_actives:
                            if isinstance(item, dict):
                                symbol = item.get('id', item.get('name', ''))
                                is_open = item.get('enabled', item.get('open', False))
                                if symbol:
                                    symbols_list.append({
                                        "symbol": symbol,
                                        "displayName": symbol.replace('-OTC', ' (OTC)'),
                                        "active": is_open,
                                        "category": "forex"
                                    })
                    
                    # Ordenar: primero los abiertos, luego por nombre
                    symbols_list.sort(key=lambda x: (not x['active'], x['symbol']))
                    
                    # Cachear resultado
                    r.symbols_data = symbols_list
                    
                    open_count = sum(1 for s in symbols_list if s['active'])
                    print(f"✅ Obtenidos {len(symbols_list)} símbolos desde IQ Option ({open_count} abiertos)")
                    
                    return jsonify({
                        "symbols": symbols_list,
                        "count": len(symbols_list),
                        "source": "iq_option_live",
                        "open_count": open_count
                    })
            except Exception as e:
                print(f"⚠️ Error obteniendo símbolos desde IQ Option: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: símbolos por defecto
        print("⚠️ No hay conexión IQ Option disponible, usando símbolos por defecto")
        default_symbols = [
            {"symbol": "EURUSD-OTC", "displayName": "EUR/USD (OTC)", "active": False, "category": "forex"},
            {"symbol": "GBPUSD-OTC", "displayName": "GBP/USD (OTC)", "active": False, "category": "forex"},
            {"symbol": "USDJPY-OTC", "displayName": "USD/JPY (OTC)", "active": False, "category": "forex"},
            {"symbol": "EURJPY-OTC", "displayName": "EUR/JPY (OTC)", "active": False, "category": "forex"},
            {"symbol": "EURUSD", "displayName": "EUR/USD", "active": False, "category": "forex"},
            {"symbol": "GBPUSD", "displayName": "GBP/USD", "active": False, "category": "forex"},
            {"symbol": "USDJPY", "displayName": "USD/JPY", "active": False, "category": "forex"},
            {"symbol": "EURJPY", "displayName": "EUR/JPY", "active": False, "category": "forex"}
        ]
        
        return jsonify({
            "symbols": default_symbols,
            "count": len(default_symbols),
            "source": "default"
        })
        
    except Exception as e:
        print(f"❌ Error en endpoint /symbols: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo símbolos: {str(e)}"}), 500

@bp.route("/balance", methods=["GET", "POST"])
def iq_balance():
    """Endpoint para obtener/actualizar el saldo de la cuenta IQ Option"""
    balance_key = "iq_session_balance"
    
    if request.method == "POST":
        # Actualizar balance (viene del iq_client.py)
        try:
            data = request.get_json(force=True, silent=True) or {}
            balance_data = data.get("balance_data")
            
            if balance_data:
                # Guardar en cache en memoria
                r.balance_data = balance_data
                print(f"💰 Balance IQ guardado: ${balance_data.get('balance', 0):.2f}")
                return jsonify({"status": "success", "balance": balance_data})
            else:
                return jsonify({"error": "No balance data provided"}), 400
                
        except Exception as e:
            return jsonify({"error": f"Error actualizando balance: {str(e)}"}), 500
    
    # GET - Obtener balance
    try:
        # Intentar obtener balance actualizado desde cuenta conectada
        for key in r.data.keys():
            if key.startswith("iq_account_"):
                account = r.data[key]
                if account.connected:
                    balance = account.get_balance()
                    r.balance_data = {
                        "balance": balance,
                        "currency": "USD",
                        "balance_type": account.account_type
                    }
                    return jsonify(r.balance_data)
        
        # Si no hay cuenta conectada, usar balance en cache
        if r.balance_data:
            return jsonify(r.balance_data)
        
        # No hay datos reales disponibles - devolver balance por defecto
        default_balance = {
            "balance": 10000.0,
            "currency": "USD",
            "balance_type": "PRACTICE"
        }
        r.balance_data = default_balance
        return jsonify(default_balance)
        
    except Exception as e:
        return jsonify(error=f"Error obteniendo balance: {str(e)}"), 500

@bp.route("/auto-connect", methods=["POST"])
def iq_auto_connect():
    """Endpoint para conectar automáticamente usando credenciales de secrets"""
    try:
        from services.account_manager import IQOptionAccount
        import os
        
        # Obtener credenciales desde secrets
        email = os.getenv("IQ_EMAIL")
        password = os.getenv("IQ_PASSWORD")
        account_type = os.getenv("IQ_BALANCE_TYPE", "PRACTICE")
        
        # Corregir typo común en IQ_BALANCE_TYPE
        if account_type == "PRACTIQUE":
            account_type = "PRACTICE"
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Credenciales no configuradas en secrets. Configura IQ_EMAIL y IQ_PASSWORD."
            }), 400
        
        # Usar email como user_id
        user_id = email
        
        print(f"🔗 [AUTO] Conectando usuario {user_id} a IQ Option ({account_type})...")
        
        # Crear cuenta de IQ Option
        account = IQOptionAccount(user_id, email, password, account_type)
        
        # Intentar conectar
        success = account.connect()
        
        if success:
            # Obtener balance actualizado
            balance = account.get_balance()
            
            # Guardar la instancia de la cuenta en el cache (r.data)
            account_key = f"iq_account_{user_id}"
            r.data[account_key] = account
            
            # Actualizar balance en cache para que el endpoint de balance lo muestre
            r.balance_data = {
                "balance": balance,
                "currency": "USD",
                "balance_type": account_type
            }
            
            print(f"✅ [AUTO] Usuario {user_id} conectado exitosamente - Balance: ${balance}")
            
            return jsonify({
                "success": True,
                "message": f"Conectado exitosamente a IQ Option ({account_type})",
                "balance": balance,
                "account_type": account_type,
                "email": email
            })
        else:
            print(f"❌ [AUTO] Falló conexión de usuario {user_id}")
            return jsonify({
                "success": False,
                "message": "Error al conectar con IQ Option. Verifica tus credenciales en secrets."
            }), 401
            
    except Exception as e:
        print(f"❌ Error en /api/iq/auto-connect: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error al conectar: {str(e)}"
        }), 500

@bp.route("/connect", methods=["POST"])
def iq_connect():
    """Endpoint para conectar con IQ Option usando credenciales del usuario"""
    try:
        from services.account_manager import IQOptionAccount
        
        data = request.get_json(force=True, silent=True) or {}
        email = data.get("email")
        password = data.get("password")
        account_type = data.get("account_type", "PRACTICE")
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email y contraseña son requeridos"
            }), 400
        
        # Usar email como user_id
        user_id = email
        
        print(f"🔗 Intentando conectar usuario {user_id} a IQ Option ({account_type})...")
        
        # Crear cuenta de IQ Option
        account = IQOptionAccount(user_id, email, password, account_type)
        
        # Intentar conectar
        success = account.connect()
        
        if success:
            # Obtener balance actualizado
            balance = account.get_balance()
            
            # Guardar la instancia de la cuenta en el cache (r.data)
            account_key = f"iq_account_{user_id}"
            r.data[account_key] = account
            
            # Actualizar balance en cache para que el endpoint de balance lo muestre
            r.balance_data = {
                "balance": balance,
                "currency": "USD",
                "balance_type": account_type
            }
            
            print(f"✅ Usuario {user_id} conectado exitosamente - Balance: ${balance}")
            
            return jsonify({
                "success": True,
                "message": f"Conectado exitosamente a IQ Option ({account_type})",
                "balance": balance,
                "account_type": account_type
            })
        else:
            print(f"❌ Falló conexión de usuario {user_id}")
            return jsonify({
                "success": False,
                "message": "Error al conectar con IQ Option. Verifica tus credenciales."
            }), 401
            
    except Exception as e:
        print(f"❌ Error en /api/iq/connect: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error al conectar: {str(e)}"
        }), 500

@bp.route("/disconnect", methods=["POST"])
def iq_disconnect():
    """
    Desconectar cuenta de IQ Option del usuario
    Elimina completamente la cuenta del cache y cierra la conexión API
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        email = data.get("email")
        
        if not email:
            # Si no se proporciona email, intentar desconectar TODAS las cuentas
            print("⚠️ No se proporcionó email - desconectando todas las cuentas")
            account_keys = [k for k in list(r.data.keys()) if k.startswith("iq_account_")]
            
            for key in account_keys:
                account = r.data[key]
                try:
                    account.disconnect()
                    print(f"🔌 Cuenta {key} desconectada")
                except:
                    pass
                del r.data[key]
            
            # Limpiar flags de streams activos
            stream_keys = [k for k in list(r.data.keys()) if k.startswith("stream_active_")]
            for stream_key in stream_keys:
                del r.data[stream_key]
                print(f"🧹 Flag de stream limpiado: {stream_key}")
            
            # Resetear balance
            r.balance_data = {"balance": 0, "currency": "USD"}
            
            return jsonify({
                "success": True,
                "message": "Todas las cuentas desconectadas"
            })
        
        # Desconectar cuenta específica del usuario
        user_id = email
        account_key = f"iq_account_{user_id}"
        
        if account_key in r.data:
            account = r.data[account_key]
            
            # Cerrar conexión API
            try:
                account.disconnect()
                print(f"🔌 Usuario {user_id} desconectado de IQ Option")
            except Exception as disc_err:
                print(f"⚠️  Error cerrando API: {disc_err}")
            
            # Eliminar cuenta del cache
            del r.data[account_key]
            
            # Limpiar flags de streams activos
            stream_keys = [k for k in list(r.data.keys()) if k.startswith("stream_active_")]
            for stream_key in stream_keys:
                del r.data[stream_key]
                print(f"🧹 Flag de stream limpiado: {stream_key}")
            
            # Resetear balance
            r.balance_data = {"balance": 0, "currency": "USD"}
            
            return jsonify({
                "success": True,
                "message": "Desconectado exitosamente"
            })
        else:
            return jsonify({
                "success": False,
                "message": "No hay cuenta conectada"
            }), 404
            
    except Exception as e:
        print(f"❌ Error en /api/iq/disconnect: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error desconectando: {str(e)}"
        }), 500

@bp.route("/candles", methods=["GET", "POST"])
def iq_candles():
    if request.method == "POST":
        # Recibir velas desde iq_client.py
        try:
            data = request.get_json(force=True, silent=True) or {}
            symbol = data.get("symbol", "EURUSD-OTC")
            timeframe = data.get("timeframe", "M5") 
            candles = data.get("candles", [])
            
            if candles:
                # Guardar velas en cache en memoria
                candles_key = f"{symbol}_{timeframe}"
                r.candles_data[candles_key] = candles
                print(f"✅ Guardadas {len(candles)} velas: {symbol} {timeframe}")
                
            return jsonify({"status": "success", "candles_stored": len(candles)})
            
        except Exception as e:
            return jsonify({"error": f"Error procesando velas: {str(e)}"}), 500
    
    # GET - Servir velas COMPARTIDAS desde PostgreSQL 
    # REQUIERE: Suscripción activa o código promocional válido
    
    # Verificar acceso
    if 'user_id' not in session:
        print("❌ ACCESO DENEGADO A VELAS: Sin sesión")
        return jsonify({'success': False, 'error': 'No autorizado. Inicia sesión primero.'}), 401
    
    user_id = session['user_id']
    print(f"🔐 [BP] Verificando acceso a velas para user_id: {user_id}")
    
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
            print(f"❌ [BP] ACCESO DENEGADO A VELAS: Usuario {user_id} sin plan ni código activo")
            return jsonify({
                'success': False,
                'error': 'Acceso denegado. Necesitas una suscripción activa o código promocional válido.',
                'requires_subscription': True
            }), 403
    
    print(f"✅ [BP] ACCESO A VELAS PERMITIDO: Usuario {user_id}")
    
    symbol = request.args.get("symbol", "EURUSD-OTC")
    timeframe = request.args.get("timeframe", "M5")
    limit = int(request.args.get("limit", 200))
    
    print(f"📊 Solicitando velas compartidas: {symbol} {timeframe} (limit={limit})")
    
    # Intentar obtener precio actual del worker global
    live_price = None
    try:
        price_key = f"live_price_{symbol}"
        if price_key in r.data:
            live_price = r.data[price_key]
            print(f"💹 Precio en vivo para {symbol}: {live_price}")
    except:
        pass
    
    # Leer velas SOLO desde Twelve Data (mercado real) en PostgreSQL
    from services.candle_service import candle_service
    candles = candle_service.get_candles(symbol, timeframe, limit, source='twelvedata', live_price=live_price)
    
    if candles and len(candles) > 0:
        print(f"✅ Sirviendo {len(candles)} velas compartidas desde PostgreSQL: {symbol}")
        return jsonify(candles)
    
    # Si no hay velas en BD, devolver array vacío (el worker las cargará pronto)
    print(f"⚠️ No hay velas en PostgreSQL para {symbol} {timeframe} - el worker las actualizará pronto")
    return jsonify([])

@app.route("/health")
def health():
    return {"status": "ok", "redis": True}

# CORS manual - Agregar headers CORS a todas las respuestas
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type,Authorization,Accept,X-Requested-With')
    response.headers['Access-Control-Allow-Methods'] = (
        'GET,PUT,POST,DELETE,OPTIONS,HEAD')
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

# Manejar preflight OPTIONS requests para todos los endpoints
@app.route('/api/iq/login', methods=['OPTIONS'])
@app.route('/api/iq/logout', methods=['OPTIONS'])
@app.route('/api/iq/session', methods=['OPTIONS'])
@app.route('/api/iq/order', methods=['OPTIONS'])  
@app.route('/api/iq/order_results', methods=['OPTIONS'])
@app.route('/api/iq/symbols', methods=['OPTIONS'])
@app.route('/api/iq/balance', methods=['OPTIONS'])
@app.route('/api/iq/candles', methods=['OPTIONS'])
@app.route('/health', methods=['OPTIONS'])
def handle_options():
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type,Authorization,Accept,X-Requested-With')
    response.headers['Access-Control-Allow-Methods'] = (
        'GET,PUT,POST,DELETE,OPTIONS,HEAD')
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

app.register_blueprint(bp)
app.register_blueprint(bot_bp)


def bot_trade_executor(symbol: str, direction: str, amount: float, duration: int) -> dict:
    """Función para ejecutar trades desde los bots"""
    try:
        request_id = str(uuid.uuid4())
        
        order_data = {
            "request_id": request_id,
            "symbol": symbol,
            "direction": direction.upper(),
            "amount": amount,
            "duration": duration,
            "timestamp": int(time.time())
        }
        
        r.rpush("iq_pending_orders", json.dumps(order_data))
        
        print(f"🤖 Bot Order: {direction} {symbol} @ ${amount} ({duration}min)")
        
        return {
            "success": True,
            "trade_id": request_id,
            "message": "Orden encolada para ejecución"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def bot_candle_provider(symbol: str, timeframe: str) -> list:
    """Función para obtener velas desde el cache para los bots"""
    try:
        from strategy_engine import Candle
        
        candles_raw = get_redis_candles(symbol, limit=200)
        
        if not candles_raw:
            return []
        
        candles = []
        for c in candles_raw:
            if isinstance(c, dict):
                candles.append(Candle(
                    time=c.get('time', 0),
                    open=c.get('open', 0.0),
                    high=c.get('high', 0.0),
                    low=c.get('low', 0.0),
                    close=c.get('close', 0.0),
                    volume=c.get('volume', 0.0)
                ))
                
        return candles
        
    except Exception as e:
        print(f"❌ Error obteniendo velas para bot: {e}")
        return []


init_bot_system(bot_trade_executor, bot_candle_provider)

def get_redis_candles(symbol: str, limit: int = 200) -> list:
    """Obtener velas desde Redis"""
    try:
        # Implementar lógica para obtener desde Redis
        # Por ahora retornamos lista vacía ya que usamos CSV
        return []
    except Exception as e:
        print(f"Error obteniendo velas desde Redis: {e}")
        return []

@app.get("/api/iq/candles")
def get_candles():
    """
    Devuelve velas globales compartidas desde Twelve Data (mercado real)
    IMPORTANTE: Estas velas son SOLO para visualización
    NO dependen de la conexión del usuario a IQ Option
    REQUIERE: Suscripción activa o código promocional válido
    """
    # Verificar acceso: usuario debe tener sesión Y (suscripción activa O código promocional válido)
    print(f"🔍 DEBUG SESSION: {dict(session)}")
    print(f"🔍 DEBUG USER_ID in session: {'user_id' in session}")
    if 'user_id' not in session:
        print("❌ ACCESO DENEGADO: Sin sesión")
        return jsonify({'success': False, 'error': 'No autorizado. Inicia sesión primero.'}), 401
    
    user_id = session['user_id']
    print(f"🔐 Verificando acceso para user_id: {user_id}")
    
    with get_db() as db:
        from database import Subscription, PromoCode, SubscriptionStatus
        
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
            print(f"❌ ACCESO DENEGADO: Usuario {user_id} sin plan ni código activo")
            return jsonify({
                'success': False,
                'error': 'Acceso denegado. Necesitas una suscripción activa o código promocional válido.',
                'requires_subscription': True
            }), 403
    
    print(f"✅ ACCESO PERMITIDO: Usuario {user_id}")
    
    symbol = request.args.get("symbol")
    tf = (request.args.get("timeframe") or "M5").upper()
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200

    if not symbol:
        return jsonify({"error": "symbol requerido"}), 400

    print(f"📊 Solicitando velas compartidas: {symbol} {tf} (limit={limit})")
    
    # Obtener velas SOLO desde Twelve Data (mercado real) en PostgreSQL
    candles = candle_service.get_candles(symbol, tf, limit, source='twelvedata')
    
    if candles:
        print(f"✅ Sirviendo {len(candles)} velas compartidas desde PostgreSQL: {symbol}")
        return jsonify(candles)
    
    print(f"⚠️ No se encontraron velas para {symbol} (source=twelvedata)")
    return jsonify([])


@app.get("/api/iq/current-candle")
def get_current_candle():
    """
    Obtener la vela actual en tiempo real desde el stream de WebSocket de IQ Option
    REQUIERE: Suscripción activa o código promocional válido
    REQUIERE: Validación de email del broker con usuario logueado
    """
    try:
        # 1. VALIDAR SESIÓN
        if 'user_id' not in session:
            print("❌ [CURRENT-CANDLE] ACCESO DENEGADO: Sin sesión")
            return jsonify({'success': False, 'error': 'No autorizado. Inicia sesión primero.'}), 401
        
        user_id = session['user_id']
        print(f"🔐 [CURRENT-CANDLE] Verificando acceso para user_id: {user_id}")
        
        # 2. VALIDAR ACCESO (PLAN O CÓDIGO ACTIVO)
        with get_db() as db:
            from database import Subscription, PromoCode, SubscriptionStatus, User
            
            # Obtener usuario con email
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            user_email = user.email
            
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
                print(f"❌ [CURRENT-CANDLE] ACCESO DENEGADO: Usuario {user_id} sin plan ni código activo")
                return jsonify({
                    'success': False,
                    'error': 'Acceso denegado. Necesitas una suscripción activa o código promocional válido.',
                    'requires_subscription': True
                }), 403
        
        print(f"✅ [CURRENT-CANDLE] ACCESO PERMITIDO: Usuario {user_id}")
        
        symbol = request.args.get("symbol")
        timeframe = request.args.get("timeframe", "M5").upper()
        
        if not symbol:
            return jsonify({"error": "symbol requerido"}), 400
        
        # 3. BUSCAR CUENTA DEL BROKER Y VALIDAR EMAIL
        account = None
        account_key = None
        
        for key, value in r.data.items():
            if key.startswith("iq_account_"):
                account = value
                account_key = key
                break
        
        if not account or not account.connected:
            return jsonify({
                "error": "No hay cuenta conectada. Usa /api/iq/connect primero.",
                "connected": False
            }), 401
        
        # 4. VALIDAR QUE EL EMAIL DEL BROKER COINCIDA CON EL USUARIO LOGUEADO
        broker_email = getattr(account, 'email', None)
        if broker_email and broker_email.lower() != user_email.lower():
            print(f"🚨 [SECURITY] EMAIL MISMATCH: Usuario {user_email} intentó usar sesión de {broker_email}")
            return jsonify({
                "success": False,
                "error": "Acceso denegado. El broker conectado no pertenece a este usuario.",
                "security_violation": True
            }), 403
        
        print(f"✅ [SECURITY] Email validado: {user_email} = {broker_email}")
        
        # Verificar si el stream ya está iniciado
        # Si no, iniciarlo
        stream_key = f"stream_active_{symbol}_{timeframe}"
        stream_active = r.data.get(stream_key, False)
        
        if not stream_active:
            print(f"📡 Iniciando stream de velas para {symbol} {timeframe}...")
            success = account.start_candle_stream(symbol, timeframe, maxdict=100)
            
            if success:
                r.data[stream_key] = True
                # NO bloquear el servidor - el buffer se llenará en los próximos segundos
                # El frontend reintentará automáticamente cada segundo
                print(f"✅ Stream iniciado - datos disponibles en ~3 segundos")
            else:
                return jsonify({
                    "error": "No se pudo iniciar el stream de velas",
                    "connected": True,
                    "stream_active": False
                }), 500
        
        # Obtener la vela actual del stream
        current_candle = account.get_current_candle(symbol, timeframe)
        
        if current_candle:
            return jsonify({
                "success": True,
                "candle": current_candle,
                "symbol": symbol,
                "timeframe": timeframe,
                "stream_active": True
            })
        else:
            return jsonify({
                "success": False,
                "error": "No hay datos de vela disponibles en el stream",
                "symbol": symbol,
                "timeframe": timeframe,
                "stream_active": True
            }), 404
            
    except Exception as e:
        print(f"❌ Error en /api/iq/current-candle: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.get("/api/olymptrade/candles")
def get_olymptrade_candles():
    """
    Obtener velas de OlympTrade usando pipeline separado
    """
    try:
        from services.olymp_pipeline import OlympTradePipeline
        
        symbol = request.args.get("symbol", "EURUSD")
        tf = request.args.get("timeframe", "M5").upper()
        try:
            limit = int(request.args.get("limit", "200"))
        except ValueError:
            limit = 200
        
        pipeline = OlympTradePipeline()
        candles = pipeline.get_candles(symbol, tf, limit, use_cache=True)
        
        if candles:
            print(f"✅ OlympTrade Pipeline: {len(candles)} velas de {symbol} (source=olymptrade)")
            return jsonify(candles)
        else:
            print(f"⚠️ OlympTrade Pipeline: Sin datos para {symbol}")
            return jsonify([])
            
    except Exception as e:
        print(f"❌ Error OlympTrade Pipeline: {e}")
        return jsonify({"error": str(e)}), 500

@app.get("/api/olymptrade/symbols")
def get_olymptrade_symbols():
    """
    Lista de símbolos disponibles en OlympTrade
    """
    symbols = [
        {"name": "EUR/USD", "symbol": "EURUSD", "type": "forex"},
        {"name": "EUR/JPY", "symbol": "EURJPY", "type": "forex"},
        {"name": "GBP/USD", "symbol": "GBPUSD", "type": "forex"},
        {"name": "USD/JPY", "symbol": "USDJPY", "type": "forex"},
        {"name": "Bitcoin USD", "symbol": "BTCUSD", "type": "crypto"}
    ]
    return jsonify(symbols)

if __name__ == "__main__":
    # Iniciar Candle Worker GLOBAL (velas compartidas para todos los usuarios)
    from services.candle_worker import candle_worker
    candle_worker.start()
    print("✅ Candle Worker Global iniciado - velas compartidas para todos los usuarios")
    
    print("[IQ ROUTES] on http://127.0.0.1:8080 (Cache: Memoria)")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)