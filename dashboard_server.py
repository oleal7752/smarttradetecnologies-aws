#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STC Dashboard Server - Version HTTP Simple
Puerto 5001 HTTP para evitar problemas de certificados SSL
"""

import os
import re
import json
import time
import ssl
import logging
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, session
from flask_sock import Sock
import websocket

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("stc-dashboard")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Inicializar WebSocket support
sock = Sock(app)

# Registrar blueprints
from auth_routes import auth_bp, requires_active_access, login_required, admin_required
from bot_routes import bot_bp
from admin_routes import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(bot_bp)
app.register_blueprint(admin_bp)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Signature')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    # NO CACHE para archivos HTML/JS - Crítico para que las actualizaciones se vean inmediatamente
    if request.path.endswith(('.html', '.js')) or '/static/' in request.path:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    
    return response

# ================= Config =================
DASHBOARD_PORT = 5000

# URLs de servicios con variables de ambiente override
IS_PRODUCTION = os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('REPLIT_DEPLOYMENT_ID') is not None

# Backend API URL (servidor a servidor)
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:8080')

# RealTime Server URLs (servidor a servidor)
REALTIME_API_URL = os.environ.get('REALTIME_API_URL', 'http://localhost:8000')
REALTIME_WS_URL = os.environ.get('REALTIME_WS_URL', 'ws://localhost:8000')

# ================= Market Data Endpoints (Públicos - No requieren autenticación) =================
@app.route("/api/market/live-candle/<path:symbol>")
def market_live_candle(symbol):
    """Obtener vela M5 ACTUAL EN CONSTRUCCIÓN desde velas M1 de Twelve Data"""
    try:
        import requests
        from datetime import datetime
        
        # Calcular timestamp M5 actual (vela en construcción)
        now_sec = int(time.time())
        current_m5_timestamp = (now_sec // 300) * 300
        
        # Usar Twelve Data para obtener últimas 6 velas M1
        api_key = os.getenv('TWELVEDATA_API_KEY')
        url = f"https://api.twelvedata.com/time_series"
        
        params = {
            'symbol': symbol,
            'interval': '1min',
            'apikey': api_key,
            'outputsize': 6,  # Últimas 6 velas M1 para cubrir M5 actual
            'format': 'JSON'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'values' not in data or not data['values']:
            return jsonify({"error": "No hay datos disponibles", "source": "twelve_data"}), 500
        
        # Filtrar solo las M1 que pertenecen al periodo M5 actual
        m1_candles = []
        for m1 in data['values']:
            # CRÍTICO: Convertir datetime string a timestamp UTC (Twelve Data devuelve UTC)
            from datetime import timezone
            dt = datetime.strptime(m1['datetime'], '%Y-%m-%d %H:%M:%S')
            dt_utc = dt.replace(tzinfo=timezone.utc)
            m1_timestamp = int(dt_utc.timestamp())
            
            # Incluir solo M1 del periodo M5 actual
            if current_m5_timestamp <= m1_timestamp < (current_m5_timestamp + 300):
                m1_candles.append({
                    'timestamp': m1_timestamp,
                    'open': float(m1['open']),
                    'high': float(m1['high']),
                    'low': float(m1['low']),
                    'close': float(m1['close'])
                })
        
        # Si no hay M1 del periodo actual, usar la última M1 disponible
        if not m1_candles:
            latest_m1 = data['values'][0]
            m5_candle = {
                "time": current_m5_timestamp,
                "open": float(latest_m1['open']),
                "high": float(latest_m1['high']),
                "low": float(latest_m1['low']),
                "close": float(latest_m1['close']),
                "timestamp": current_m5_timestamp,
                "source": "Twelve Data (M1 fallback)",
                "m1_count": 0
            }
        else:
            # Ordenar M1 cronológicamente (más antigua primero)
            m1_candles_sorted = sorted(m1_candles, key=lambda x: x['timestamp'])
            
            # Construir vela M5 desde M1
            m5_candle = {
                "time": current_m5_timestamp,
                "open": m1_candles_sorted[0]['open'],  # Primera M1 = open
                "high": max(c['high'] for c in m1_candles_sorted),
                "low": min(c['low'] for c in m1_candles_sorted),
                "close": m1_candles_sorted[-1]['close'],  # Última M1 = close
                "timestamp": current_m5_timestamp,
                "source": "Twelve Data (M1→M5 Live)",
                "m1_count": len(m1_candles_sorted)
            }
        
        return jsonify(m5_candle)
        
    except Exception as e:
        logger.error(f"Error construyendo vela M5 en tiempo real: {e}")
        return jsonify({"error": str(e), "source": "twelve_data"}), 500

@app.route("/api/market/realtime-price/<path:symbol>")
def market_realtime_price(symbol):
    """Obtener precio en TIEMPO REAL desde IQ Option (sin delay)"""
    try:
        from iq_client import iq_client
        
        # Verificar que IQ Option esté conectado
        if not iq_client.connected:
            return jsonify({"error": "IQ Option no conectado"}), 503
        
        # Convertir símbolo al formato IQ Option
        iq_symbol = symbol.replace('/', '').upper()  # EUR/USD -> EURUSD
        
        # Obtener última vela M1 desde IQ Option (casi en tiempo real)
        candles = iq_client.get_candles(iq_symbol, timeframe="M1", limit=1)
        
        if not candles or len(candles) == 0:
            return jsonify({"error": "No se pudo obtener precio de IQ Option"}), 500
        
        latest = candles[0]
        
        return jsonify({
            "symbol": symbol,
            "price": latest['close'],
            "open": latest['open'],
            "high": latest['high'],
            "low": latest['low'],
            "close": latest['close'],
            "timestamp": latest['timestamp'],
            "source": "IQ Option (Real-Time)"
        })
    except Exception as e:
        logger.error(f"Error obteniendo precio IQ Option: {e}")
        return jsonify({"error": str(e)}), 500

# ================= Rutas Dashboard =================
@app.route("/favicon.ico")
def favicon():
    """Ruta para favicon - retorna 204 No Content para evitar error 404"""
    return '', 204

@app.route("/")
def root():
    return render_template("landing.html")

@app.route("/setup-admin-now")
def setup_admin_now():
    """Endpoint temporal para crear admin en producción"""
    from werkzeug.security import generate_password_hash
    from database import get_db, User
    import uuid
    from datetime import datetime, timedelta
    
    try:
        with get_db() as db:
            # Verificar si ya existe
            admin = db.query(User).filter_by(email="admin@stc.com").first()
            
            if admin:
                # Actualizar contraseña
                admin.password_hash = generate_password_hash("admin123")
                admin.email_verified = True
                admin.is_admin = True
                admin.is_active = True
                db.commit()
                return jsonify({
                    "success": True,
                    "message": "Admin actualizado",
                    "email": "admin@stc.com",
                    "password": "admin123"
                })
            else:
                # Crear nuevo
                new_admin = User(
                    id=str(uuid.uuid4()),
                    email="admin@stc.com",
                    password_hash=generate_password_hash("admin123"),
                    first_name="Super",
                    last_name="Admin",
                    dni="99999999",
                    birth_date=(datetime.now() - timedelta(days=365*30)).date(),
                    phone="+999999999",
                    country="System"
                )
                new_admin.email_verified = True
                new_admin.is_admin = True
                new_admin.is_active = True
                db.add(new_admin)
                db.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Admin creado exitosamente",
                    "email": "admin@stc.com",
                    "password": "admin123"
                })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/landing")
def landing_page():
    return render_template("landing.html")

@app.route("/dashboard")
@login_required
@requires_active_access
def dashboard_page():
    """Dashboard principal
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("dashboard_pro.html")

@app.route("/dashboard_old")
@login_required
@requires_active_access
def dashboard_old():
    """Dashboard legacy
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("dashboard.html")

@app.route("/dashboard_candles_signals.html")
def legacy_dashboard_redirect():
    return redirect(url_for('dashboard_page'), code=302)

@app.route("/stable")
@login_required
@requires_active_access
def dashboard_stable():
    """Dashboard estable legacy
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("dashboard_stable.html")

@app.route("/signals")
@login_required
@requires_active_access
def signals_panel():
    """Panel de señales en tiempo real - Multi-símbolo
    REQUIERE: Sesión activa + suscripción/código válido"""
    api_key = os.getenv("BOT_API_KEY", "stc_default_key_2025")
    return render_template("signals_panel.html", api_key=api_key)

@app.route("/candles-demo")
def candles_demo_public():
    """Panel de velas japonesas PÚBLICO - Sin autenticación
    Versión DEMO para pruebas sin login"""
    api_key = os.getenv("BOT_API_KEY", "stc_default_key_2025")
    return render_template("dashboard_stable.html", api_key=api_key)

@app.route("/bot-manager")
@login_required
@requires_active_access
def bot_manager_panel():
    """Panel de gestión de operaciones del bot
    REQUIERE: Sesión activa + suscripción/código válido"""
    # Leer API key del entorno (mismo valor que usa el servidor realtime)
    api_key = os.getenv("BOT_API_KEY", "stc_default_key_2025")
    return render_template("bot_manager.html", api_key=api_key)

@app.route("/charts-test")
@login_required
@requires_active_access
def charts_test():
    """Test de gráficos
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("dashboard_stable.html")

@app.route("/dashboard-modern")
@login_required
@requires_active_access
def dashboard_modern():
    """Dashboard moderno con arquitectura limpia y modular
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("dashboard_modern.html")

@app.route("/bot-panel")
@login_required
@requires_active_access
def bot_panel():
    """Panel de bots
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("bot_panel.html")

@app.route("/bots")
@login_required
@requires_active_access
def bots_page():
    """Página de bots
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("bot_panel.html")

@app.route("/backtests")
@login_required
@requires_active_access
def master_backtest_page():
    """Página de backtests maestros inteligentes
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("master_backtest.html")

@app.route("/monitor")
@login_required
@requires_active_access
def monitor_page():
    """Panel de monitoreo
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("monitor_dashboard.html")

@app.route("/auth/verify-email")
def verify_email_page():
    """Página de verificación de email"""
    return render_template("verify_email.html")

@app.route("/auth/login")
def login_page():
    """Página de inicio de sesión"""
    return render_template("login.html")

@app.route("/broker-status")
@login_required
def broker_status_page():
    """Página de estado de validación de broker
    REQUIERE: Sesión activa"""
    return render_template("broker_status.html")

@app.route("/admin/broker-validation")
@login_required
@admin_required
def admin_broker_validation_page():
    """Panel de administración para validar brokers
    REQUIERE: Sesión activa + permisos de administrador"""
    return render_template("admin_broker_validation.html")

@app.route("/admin/promo-codes")
@login_required
@admin_required
def admin_promo_codes_page():
    """Panel de administración para gestionar códigos promocionales
    REQUIERE: Sesión activa + permisos de administrador"""
    return render_template("admin_promo_codes.html")

@app.route("/subscriptions")
@login_required
def subscriptions_page():
    """Página de suscripciones
    REQUIERE: Sesión activa"""
    return render_template("subscriptions.html")

@app.route("/access-validation")
@login_required
def access_validation_page():
    """Página de validación de acceso post-login
    REQUIERE: Sesión activa"""
    return render_template("access_validation.html")

@app.route("/welcome")
@login_required
@requires_active_access
def welcome_page():
    """Página de bienvenida después de validar acceso
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("welcome.html")

@app.route("/trading-charts")
@login_required
def trading_charts_page():
    """Página de bienvenida a zona de operaciones con bandera Venezuela
    REQUIERE: Solo sesión activa (aquí el usuario ingresa código si no tiene acceso)"""
    return render_template("trading_charts.html")

@app.route("/charts")
@login_required
@requires_active_access
def charts_redirect():
    """Redirige a la zona de gráficos profesionales
    REQUIERE: Sesión activa + suscripción/código válido"""
    return redirect("/static/demo/candlestick.html")

# ================= Selector de Broker =================
ALLOWED_BROKERS = ['iqoption', 'olymptrade']

@app.route("/select-broker", methods=['GET'])
@login_required
@requires_active_access
def broker_selector_page():
    """Página de selección de broker
    REQUIERE: Sesión activa + suscripción/código válido"""
    return render_template("broker_selector.html")

@app.route("/select-broker", methods=['POST'])
@login_required
@requires_active_access
def select_broker():
    """Guardar selección de broker en sesión y redirigir al dashboard correspondiente
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        data = request.json
        broker = data.get('broker', '').lower()
        
        if broker not in ALLOWED_BROKERS:
            return jsonify({
                'success': False,
                'error': f'Broker no válido. Opciones: {", ".join(ALLOWED_BROKERS)}'
            }), 400
        
        session['active_broker'] = broker
        
        redirect_url = f'/dashboard/{broker}'
        
        return jsonify({
            'success': True,
            'broker': broker,
            'redirect': redirect_url
        })
    except Exception as e:
        logger.error(f"Error al seleccionar broker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/broker/select/<broker>")
@login_required
@requires_active_access
def select_broker_get(broker):
    """Seleccionar broker vía GET y redirigir al dashboard
    REQUIERE: Sesión activa + suscripción/código válido"""
    broker = broker.lower()
    
    if broker not in ALLOWED_BROKERS:
        logger.error(f"Broker inválido: {broker}")
        return redirect(url_for('broker_selector_page'))
    
    session['active_broker'] = broker
    logger.info(f"✅ Broker seleccionado: {broker}")
    return redirect(f'/dashboard/{broker}')

@app.route("/broker/switch")
@login_required
@requires_active_access
def switch_broker():
    """Limpiar broker de sesión y volver al selector
    REQUIERE: Sesión activa + suscripción/código válido"""
    session.pop('active_broker', None)
    return redirect(url_for('broker_selector_page'))

# ================= DEMO HELPER ELIMINADO POR SEGURIDAD =================
# VULNERABILIDAD CRÍTICA: Auto-login permitía bypass del sistema de autenticación
# Las siguientes rutas han sido DESHABILITADAS permanentemente:
# - /auth/demo-direct
# - /api/auto-login-demo
# Motivo: Establecían sesión hardcodeada de Diego sin validación

# ================= Dashboards específicos por broker =================
# FINNHUB ELIMINADO - Ya no está disponible como broker

@app.route("/dashboard/iqoption")
@login_required
@requires_active_access
def dashboard_iqoption():
    """Dashboard RealTime - Trading en tiempo real con Twelve Data WebSocket
    REQUIERE: Sesión activa + suscripción/código válido"""
    if 'active_broker' not in session or session['active_broker'] != 'iqoption':
        return redirect(url_for('broker_selector_page'))
    
    # Verificar si ya tiene parámetro v (cache buster), si no, redirigir con timestamp
    import time
    if 'v' not in request.args:
        return redirect(f'/dashboard/iqoption?v={int(time.time())}')
    
    # Forzar recarga sin caché con timestamp
    response = app.make_response(render_template("dashboard_realtime.html", cache_bust=int(time.time())))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/dashboard/olymptrade")
@login_required
@requires_active_access
def dashboard_olymptrade():
    """Dashboard de OlympTrade - Trading completo
    REQUIERE: Sesión activa + suscripción/código válido"""
    if 'active_broker' not in session or session['active_broker'] != 'olymptrade':
        return redirect(url_for('broker_selector_page'))
    return render_template("dashboard_olymptrade.html")

# ================= Info / Salud =================
@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({
        "service": "STC Dashboard",
        "version": "1.0",
        "status": "running",
        "port": DASHBOARD_PORT,
        "protocol": "HTTP"
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "STC Dashboard", 
        "timestamp": time.time()
    })

@app.route('/api/server_time', methods=['GET'])
def server_time():
    """Devuelve el timestamp del servidor en UTC-5 para sincronización de velas"""
    # Obtener timestamp actual en UTC
    utc_now = datetime.now(timezone.utc)
    # Ajustar a UTC-5
    utc5_now = utc_now - timedelta(hours=5)
    # Convertir a Unix timestamp
    timestamp = int(utc5_now.timestamp())
    
    return jsonify({
        "timestamp": timestamp,
        "timezone": "UTC-5",
        "datetime": utc5_now.strftime("%Y-%m-%d %H:%M:%S")
    })

# ================= Endpoint Público de Velas (Sin Autenticación) =================
from services.candle_service import candle_service

@app.route('/api/public/candles', methods=['GET'])
def public_candles():
    """
    ENDPOINT PÚBLICO - Sirve velas de mercado en tiempo real desde PostgreSQL
    Las velas son datos públicos del mercado actualizados por Twelve Data
    NO REQUIERE AUTENTICACIÓN - Solo las señales de bots están protegidas
    
    Parámetros:
    - symbol: Símbolo del par (ej: EURUSD, BTCUSD)
    - timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
    - limit: Número de velas (default: 200, max: 1000)
    - source: Fuente de datos (twelvedata, finnhub, iqoption)
    """
    try:
        symbol = request.args.get('symbol', 'EURUSD')
        timeframe = request.args.get('timeframe', 'M5')
        limit = min(int(request.args.get('limit', 200)), 1000)  # Max 1000 velas
        source = request.args.get('source', 'twelvedata')  # Default: Twelve Data
        
        # Obtener velas desde PostgreSQL (actualizado por Twelve Data Worker)
        all_candles = candle_service.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit * 2,  # Pedir el doble para asegurar suficientes velas continuas
            source=source
        )
        
        if not all_candles:
            logger.warning(f"⚠️ No hay velas disponibles para {symbol} {timeframe} (source: {source})")
            return jsonify([]), 200
        
        # FILTRAR: Solo velas continuas sin gaps (elimina fines de semana)
        timeframe_seconds = {'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
        interval = timeframe_seconds.get(timeframe, 300)
        max_gap = interval * 2  # Permitir máximo 2x el intervalo como gap
        
        # Filtrar desde la última vela hacia atrás hasta encontrar un gap grande
        continuous_candles = []
        for i in range(len(all_candles)):
            continuous_candles.append(all_candles[i])
            
            # Si hay otra vela anterior, verificar el gap
            if i + 1 < len(all_candles):
                current_time = all_candles[i]['time']
                previous_time = all_candles[i + 1]['time']
                gap = current_time - previous_time
                
                # Si encontramos un gap grande (ej: fin de semana), detenernos
                if gap > max_gap:
                    break
        
        # Limitar al número solicitado
        candles = continuous_candles[:limit]
        
        logger.info(f"✅ Servidas {len(candles)} velas continuas (filtradas de {len(all_candles)}): {symbol} {timeframe}")
        return jsonify(candles), 200
        
    except Exception as e:
        logger.error(f"❌ Error en endpoint público de velas: {e}")
        return jsonify({"error": "Error obteniendo velas", "details": str(e)}), 500

# ================= Rutas de API Proxy =================
import requests

@app.route('/api/iq/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_iq_api(path):
    """Proxy requests to the main API server on port 5002
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/iq/{path}"
        print(f"🔄 PROXY: {request.method} {path} - Cookies: {list(request.cookies.keys())}")
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, cookies=request.cookies, timeout=30)
        elif request.method == 'POST':
            json_data = request.json if request.json else {}
            response = requests.post(api_url, json=json_data, cookies=request.cookies, timeout=30)
        elif request.method == 'PUT':
            json_data = request.json if request.json else {}
            response = requests.put(api_url, json=json_data, cookies=request.cookies, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(api_url, cookies=request.cookies, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to API: {e}")
        return jsonify({"error": "API not available", "details": str(e)}), 503

@app.route('/api/olymptrade/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_olymptrade_api(path):
    """Proxy requests to OlympTrade API on port 5002
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/olymptrade/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, cookies=request.cookies, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, cookies=request.cookies, timeout=30)
        elif request.method == 'PUT':
            response = requests.put(api_url, json=request.json, cookies=request.cookies, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(api_url, cookies=request.cookies, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to OlympTrade API: {e}")
        return jsonify({"error": "OlympTrade API not available", "details": str(e)}), 503

@app.route('/api/strategies/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_strategies_api(path):
    """Proxy requests to strategies API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/strategies/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, cookies=request.cookies, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, cookies=request.cookies, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to strategies API: {e}")
        return jsonify({"error": "Strategies API not available", "details": str(e)}), 503

@app.route('/api/bots/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_bots_api(path):
    """Proxy requests to bots API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/bots/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        headers = {'Content-Type': 'application/json'}
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, cookies=request.cookies, timeout=30)
        elif request.method == 'POST':
            # Enviar JSON vacío si no hay body
            json_data = request.json if request.json else {}
            response = requests.post(api_url, json=json_data, headers=headers, cookies=request.cookies, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(api_url, cookies=request.cookies, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to bots API: {e}")
        return jsonify({"error": "Bots API not available", "details": str(e)}), 503

@app.route('/api/backtest/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_backtest_api(path):
    """Proxy requests to backtest API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/backtest/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to backtest API: {e}")
        return jsonify({"error": "Backtest API not available", "details": str(e)}), 503

@app.route('/api/symbols/<path:path>', methods=['GET', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_symbols_api(path):
    """Proxy requests to symbols API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/symbols/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        response = requests.get(api_url, params=request.args, timeout=30)
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to symbols API: {e}")
        return jsonify({"error": "Symbols API not available", "details": str(e)}), 503

@app.route('/api/candles/<path:path>', methods=['GET', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_candles_api(path):
    """Proxy requests to candles API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/candles/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        response = requests.get(api_url, params=request.args, timeout=30)
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to candles API: {e}")
        return jsonify({"error": "Candles API not available", "details": str(e)}), 503

@app.route('/api/signals/tablero', methods=['GET'])
@login_required
@requires_active_access
def get_tablero_signals():
    """Obtiene señales de la estrategia Tablero Binarias para mostrar en el gráfico
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        symbol = request.args.get('symbol', 'EURUSD-OTC')
        timeframe = request.args.get('timeframe', 'M5')
        
        # Obtener señales del backend
        api_url = f"{BACKEND_API_URL}/api/signals/tablero"
        response = requests.get(api_url, params={'symbol': symbol, 'timeframe': timeframe}, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error obteniendo señales Tablero: {e}")
        return jsonify({"error": "Error obteniendo señales", "details": str(e)}), 503

@app.route('/api/monitor/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_monitor_api(path):
    """Proxy requests to monitor API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/monitor/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to monitor API: {e}")
        return jsonify({"error": "Monitor API not available", "details": str(e)}), 503

@app.route('/api/finnhub/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_finnhub_api(path):
    """Proxy requests to Finnhub API
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        api_url = f"{BACKEND_API_URL}/api/finnhub/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to Finnhub API: {e}")
        return jsonify({"error": "Finnhub API not available", "details": str(e)}), 503

@app.route('/api/proxy/twelvedata', methods=['GET'])
def proxy_twelvedata():
    """
    ENDPOINT PÚBLICO - Proxy para Twelve Data API (sin autenticación)
    Protege la API key del cliente mientras permite acceso público a datos de mercado
    """
    try:
        import requests
        import os
        
        api_key = os.getenv('TWELVEDATA_API_KEY')
        if not api_key:
            return jsonify({"error": "Twelve Data API key no configurada"}), 500
        
        symbol = request.args.get('symbol', 'EUR/USD')
        interval = request.args.get('interval', '5min')
        outputsize = request.args.get('outputsize', '100')
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'outputsize': outputsize,
            'apikey': api_key
        }
        
        response = requests.get(
            'https://api.twelvedata.com/time_series',
            params=params,
            timeout=10
        )
        
        return response.json(), response.status_code
        
    except Exception as e:
        logger.error(f"Error proxying to Twelve Data API: {e}")
        return jsonify({"error": "Twelve Data API not available", "details": str(e)}), 503

@app.route('/api/signals/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_signals_api(path):
    """Proxy requests to RealTime Server (puerto 8000)
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        import requests
        api_url = f"{REALTIME_API_URL}/api/signals/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        if request.method == 'GET':
            response = requests.get(api_url, params=request.args, timeout=30)
        elif request.method == 'POST':
            response = requests.post(api_url, json=request.json, timeout=30)
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to RealTime API: {e}")
        return jsonify({"error": "RealTime API not available", "details": str(e)}), 503

@app.route('/api/bot/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
@requires_active_access
def proxy_bot_api(path):
    """Proxy bot control requests to RealTime Server (puerto 8000)
    REQUIERE: Sesión activa + suscripción/código válido"""
    try:
        import requests
        api_url = f"{REALTIME_API_URL}/api/bot/{path}"
        
        if request.method == 'OPTIONS':
            return '', 200
        
        # Copiar headers relevantes (especialmente Authorization)
        headers = {
            'Content-Type': request.headers.get('Content-Type', 'application/json')
        }
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
        
        # Obtener body JSON de forma segura (sin excepción si no hay JSON)
        json_body = request.get_json(silent=True)
        
        logger.info(f"🔄 Proxy Bot API: {request.method} {api_url}")
        logger.info(f"   Headers: {headers}")
        logger.info(f"   Body: {json_body}")
        
        if request.method == 'GET':
            response = requests.get(api_url, headers=headers, params=request.args, timeout=30)
        elif request.method == 'POST':
            # Solo enviar json si existe, no enviar body vacío
            if json_body:
                response = requests.post(api_url, headers=headers, json=json_body, timeout=30)
            else:
                response = requests.post(api_url, headers=headers, timeout=30)
        
        logger.info(f"   Response: {response.status_code}")
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error proxying to Bot API: {e}")
        return jsonify({"error": "Bot API not available", "details": str(e)}), 503

@sock.route('/ws/live')
def websocket_proxy(ws):
    """Proxy WebSocket to RealTime Server (puerto 8000)
    REQUIERE: Sesión activa + suscripción/código válido"""
    
    # VALIDACIÓN DE SESIÓN Y ACCESO
    if 'user_id' not in session:
        logger.warning("❌ WebSocket: Acceso denegado - Sin sesión activa")
        ws.close(reason="No autorizado. Inicia sesión.")
        return
    
    # Verificar suscripción activa O código promocional válido
    from database import get_db, Subscription, PromoCode, SubscriptionStatus
    from datetime import datetime
    
    user_id = session['user_id']
    has_access = False
    
    with get_db() as db:
        # Verificar suscripción activa
        has_subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > datetime.utcnow()
        ).first() is not None
        
        if has_subscription:
            has_access = True
            logger.info(f"✅ WebSocket: Acceso autorizado por suscripción activa - Usuario {user_id}")
        else:
            # Verificar código promocional válido
            promo_code = db.query(PromoCode).filter(
                PromoCode.assigned_to == user_id,
                PromoCode.is_used == True,
                PromoCode.is_active == True,
                PromoCode.expires_at > datetime.utcnow()
            ).order_by(PromoCode.activated_at.desc()).first()
            
            if promo_code:
                has_access = True
                logger.info(f"✅ WebSocket: Acceso autorizado por código promocional - Usuario {user_id}")
    
    # ENFORCE: Si no tiene acceso, cerrar conexión inmediatamente
    if not has_access:
        logger.warning(f"❌ WebSocket: Acceso DENEGADO - Usuario {user_id} sin suscripción ni código válido")
        ws.close(reason="Acceso denegado. Necesitas una suscripción activa o código promocional válido.")
        return
    
    # WebSocket conectado - usar heartbeat simple (sin proxy problemático)
    try:
        logger.info("📱 Cliente WebSocket conectado (modo heartbeat simple)")
        
        # Enviar confirmación de conexión
        ws.send(json.dumps({
            "type": "connected",
            "message": "Dashboard usando HTTP polling para datos",
            "timestamp": int(time.time())
        }))
        
        # Mantener conexión viva con heartbeat cada 30 segundos
        import time
        while True:
            time.sleep(30)
            try:
                ws.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": int(time.time())
                }))
            except:
                # Conexión cerrada
                break
                
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
    finally:
        logger.info("📴 Cliente WebSocket desconectado")

def run_dashboard():
    # Conectar IQ Option automáticamente al inicio
    try:
        from iq_client import iq_client
        logger.info("🔌 Conectando a IQ Option para feeds en tiempo real...")
        
        result = iq_client.connect()
        if result.get('success'):
            logger.info(f"✅ IQ Option conectado - Balance: ${result.get('balance', 0)} ({result.get('balance_type', 'PRACTICE')})")
        else:
            logger.warning(f"⚠️ No se pudo conectar a IQ Option: {result.get('error', 'Unknown')}")
            logger.warning("📊 Dashboard funcionará con Twelve Data como fallback")
    except Exception as e:
        logger.error(f"❌ Error al conectar IQ Option: {e}")
        logger.warning("📊 Dashboard funcionará con Twelve Data como fallback")
    
    print(f"🌐 STC Dashboard iniciando en puerto {DASHBOARD_PORT}")
    print(f"📊 Acceso: http://localhost:{DASHBOARD_PORT}")
    app.run(host='0.0.0.0', port=DASHBOARD_PORT, debug=False)

if __name__ == '__main__':
    run_dashboard()
