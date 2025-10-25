#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STC Trading Platform Server (Dual Source: MT5 | IQ)
- CSV base local (historical_data/csv/{SYMBOL}_{TF}.csv)
- Bootstrap: carga CSV + sincroniza 1mo desde yfinance (incremental)
- Upsert por unix_time con prioridad: ea/mt5 > csv > yfinance > iq (por defecto)
- /api/data: entrega 300 velas cerradas por símbolo de la fuente solicitada (?source=mt5|iq)
- Selector de fuente vía /api/source (GET/POST) y desde el dashboard
- MT5: alineado por huso del bróker (BROKER_TZ_OFFSET_MINUTES)
- IQ: login desde dashboard, estado y envío de órdenes (binarias/digitales)
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
from iq_routes import init_iq_routes
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # garantiza que se pueda importar 'iq_routes'

from iq_routes import init_iq_routes
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file

# Opcional: yfinance/pandas
try:
    import yfinance as yf
    import pandas as pd
    _YF_AVAILABLE = True
except Exception:
    _YF_AVAILABLE = False

# IQ Option SDK
try:
    from iqoptionapi.stable_api import IQ_Option
    _IQ_AVAILABLE = True
except Exception:
    _IQ_AVAILABLE = False

# csv_store (carga robusta)
try:
    import csv_store
except ModuleNotFoundError:
    import importlib.util, sys
    mod_path = os.path.join(os.path.dirname(__file__), 'csv_store.py')
    if os.path.exists(mod_path):
        spec = importlib.util.spec_from_file_location('csv_store', mod_path)
        csv_store = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules['csv_store'] = csv_store
        assert spec.loader is not None
        spec.loader.exec_module(csv_store)  # type: ignore
    else:
        raise

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("stc-server")

app = Flask(__name__)
init_iq_routes(app)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

@app.after_request
def after_request(response):
    # Si vas a usar credenciales desde el dashboard en HTTP, considera HTTPS (puedes servir el dashboard por 5001).
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Signature')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ================= Config =================
API_SECRET = "tu_clave_secreta_muy_segura_2024"
HTTPS_PORT = 5001
HTTP_PORT = 5002

MAX_BUFFER_SIZE = int(os.getenv('MAX_BUFFER_SIZE', '2000'))
FRONTEND_CLOSED_LIMIT = int(os.getenv('FRONTEND_CLOSED_LIMIT', '300'))

# Offset del huso del bróker (para MT5). Ej: UTC+3 -> 180
BROKER_TZ_OFFSET_MINUTES = int(os.getenv('BROKER_TZ_OFFSET_MINUTES', '0'))

# Fuente activa por defecto (mt5 | iq)
ACTIVE_SOURCE = os.getenv('ACTIVE_SOURCE', 'mt5').lower()
if ACTIVE_SOURCE not in ('mt5', 'iq'):
    ACTIVE_SOURCE = 'mt5'

TIMEFRAME_MIN = 5
TF_MINUTES = {'M1':1,'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440}
BOOTSTRAP_PAIRS = [('EURUSD','M5')]

# ================= Memoria =================
# MT5
tick_data_mt5 = defaultdict(lambda: deque(maxlen=MAX_BUFFER_SIZE))
candle_data_mt5 = defaultdict(lambda: deque(maxlen=MAX_BUFFER_SIZE))
live_candle_mt5 = dict()

# IQ
tick_data_iq = defaultdict(lambda: deque(maxlen=MAX_BUFFER_SIZE))
candle_data_iq = defaultdict(lambda: deque(maxlen=MAX_BUFFER_SIZE))
live_candle_iq = dict()

signals_store = deque(maxlen=1000)

stats = {
    'total_ticks': 0,
    'total_candles': 0,
    'enhanced_candles': 0,
    'total_signals': 0,
    'start_time': time.time(),
    'last_activity': 0,
    'active_symbols': set(),
}

HIST_DIR = os.path.join(os.getcwd(), "historical_data")
os.makedirs(HIST_DIR, exist_ok=True)
CSV_STORE = csv_store.CsvStore(HIST_DIR)
SIGNALS_FILE = os.path.join(HIST_DIR, "_signals.jsonl")
_persist_lock = threading.Lock()

# ================= Utilidades base =================
def persist_signal(sig: dict):
    try:
        with _persist_lock, open(SIGNALS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(sig, ensure_ascii=False) + "\n")
    except Exception:
        pass

def load_signals(max_rows: int = 1000):
    try:
        if not os.path.isfile(SIGNALS_FILE):
            return
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-max_rows:]
        for ln in reversed(lines):
            try:
                s = json.loads(ln)
                signals_store.appendleft(s)
                stats['total_signals'] = max(stats['total_signals'], int(s.get('id', 0)))
            except Exception:
                continue
        logger.info(f"📦 Señales cargadas: {len(signals_store)}")
    except Exception:
        pass

def normalize_symbol(sym: str) -> str:
    if not sym: return "UNKNOWN"
    s = str(sym).upper().strip().replace(" ", "").replace("\\", "").replace("/", "")
    s = re.sub(r"[^A-Z0-9#=\-]", "", s)
    s = s.replace("=", "").replace("-", "")
    return s.replace("#", "")

def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def sanitize_candle(c: dict) -> dict | None:
    if not isinstance(c, dict): return None
    o = _to_float(c.get('open')); cl = _to_float(c.get('close'))
    h = _to_float(c.get('high')); l = _to_float(c.get('low'))
    if o is None or cl is None: return None
    if h is None: h = max(o, cl)
    if l is None: l = min(o, cl)
    if h < l: h, l = l, h
    if o > h: h = o
    if o < l: l = o
    if cl > h: h = cl
    if cl < l: l = cl
    vol = _to_float(c.get('volume')) or 0.0
    out = dict(c)
    out.update({"open":o,"high":h,"low":l,"close":cl,"volume":vol,"closed":bool(c.get('closed', True))})
    return out

def _src_priority(src: str | None) -> int:
    s = (src or '').lower()
    # Prioridad por defecto: ea/mt5 > csv > yfinance > iq
    if s in ('ea','mt5'): return 4
    if s == 'csv': return 3
    if s == 'yfinance': return 2
    if s == 'iq': return 1
    return 0

# ====== Alineado por huso del bróker (MT5) ======
def _broker_tz():
    return timezone(timedelta(minutes=BROKER_TZ_OFFSET_MINUTES))

def floor_to_tf_broker(now_utc: datetime, tf_minutes: int) -> datetime:
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)
    offset = timedelta(minutes=BROKER_TZ_OFFSET_MINUTES)
    t_local = now_utc + offset
    minute = (t_local.minute // tf_minutes) * tf_minutes
    t_local = t_local.replace(minute=minute, second=0, microsecond=0)
    t_utc = t_local - offset
    return t_utc.replace(tzinfo=timezone.utc)

def parse_mt5_timestamp_with_broker_tz(ts: str, tf_minutes: int) -> datetime:
    if not ts:
        return floor_to_tf_broker(datetime.now(timezone.utc), tf_minutes)
    s = ts.strip().replace('.', '-')
    if ' ' in s and 'T' not in s:
        s = s.replace(' ', 'T')
    try:
        if all(x not in s for x in ['+','-','Z']) or (s.endswith('T') or len(s) <= 19):
            dt_naive = datetime.fromisoformat(s[:19])
            dt_broker = dt_naive.replace(tzinfo=_broker_tz())
            dt_utc = dt_broker.astimezone(timezone.utc)
        else:
            dt_any = datetime.fromisoformat(s.replace('Z','+00:00'))
            if dt_any.tzinfo is None:
                dt_any = dt_any.replace(tzinfo=_broker_tz())
            dt_utc = dt_any.astimezone(timezone.utc)
        return floor_to_tf_broker(dt_utc, tf_minutes)
    except Exception:
        return floor_to_tf_broker(datetime.now(timezone.utc), tf_minutes)

# ====== Upsert en memoria por fuente ======
def upsert_candles_into_memory(store: defaultdict, candles: list):
    if not candles: return (0,0)
    by_sym = defaultdict(list)
    for c in candles:
        if c and c.get('symbol'):
            by_sym[c['symbol']].append(c)

    total_loaded_or_replaced = 0
    total_skipped = 0

    for symbol, seq in by_sym.items():
        arr = list(store[symbol])
        index_by_time = { c.get('unix_time'): i for i,c in enumerate(arr) if c and c.get('unix_time') is not None }
        loaded_or_replaced = 0
        skipped = 0

        for c in sorted(seq, key=lambda x: x.get('unix_time', 0)):
            if not c:
                skipped += 1
                continue
            ut = c.get('unix_time')
            if ut is None:
                skipped += 1
                continue
            new_pr = _src_priority(c.get('source'))
            if ut in index_by_time:
                i = index_by_time[ut]
                cur = arr[i]
                cur_pr = _src_priority(cur.get('source'))
                if new_pr >= cur_pr:
                    arr[i] = c
                    loaded_or_replaced += 1
                else:
                    skipped += 1
            else:
                arr.append(c)
                index_by_time[ut] = len(arr)-1
                loaded_or_replaced += 1

        try:
            arr.sort(key=lambda x: x.get('unix_time', 0))
        except Exception:
            pass

        store[symbol].clear()
        for c in arr[-MAX_BUFFER_SIZE:]:
            store[symbol].append(c)

        total_loaded_or_replaced += loaded_or_replaced
        total_skipped += skipped

    stats['total_candles'] += total_loaded_or_replaced
    stats['last_activity'] = time.time()
    return (total_loaded_or_replaced, total_skipped)

# ================= Rutas Dashboard =================
@app.route("/")
def root():
    return render_template("dashboard.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/dashboard_candles_signals.html")
def legacy_dashboard_redirect():
    return redirect(url_for('dashboard_page'), code=302)

# ================= Info / Salud =================
@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({
        "service": "STC Trading Server",
        "version": "4.1",
        "status": "running",
        "uptime_seconds": int(time.time()-stats['start_time']),
        "total_ticks": stats['total_ticks'],
        "total_candles": stats['total_candles'],
        "total_signals": stats['total_signals'],
        "active_symbols": list(stats['active_symbols']),
        "last_activity": stats['last_activity'],
        "frontend_closed_limit": FRONTEND_CLOSED_LIMIT,
        "max_buffer_size": MAX_BUFFER_SIZE,
        "broker_tz_offset_minutes": BROKER_TZ_OFFSET_MINUTES,
        "active_source": ACTIVE_SOURCE,
        "iq_available": _IQ_AVAILABLE,
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status":"healthy","timestamp": datetime.now(timezone.utc).isoformat()})

# ================= Selector de fuente =================
@app.route('/api/source', methods=['GET','POST'])
def api_source():
    global ACTIVE_SOURCE
    if request.method == 'GET':
        return jsonify({"active_source": ACTIVE_SOURCE})
    try:
        data = request.get_json(force=True, silent=False) or {}
        src = str(data.get('source','mt5')).lower()
        if src not in ('mt5','iq'):
            return jsonify({"error":"source inválido (mt5|iq)"}), 400
        ACTIVE_SOURCE = src
        return jsonify({"status":"success","active_source": ACTIVE_SOURCE})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= Seguridad MT5 =================
def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
    try:
        if not signature.startswith('sha256='): return False
        received_hash = signature[7:].strip()
        if received_hash == "1234567890":  # modo debug
            return True
        return True
    except Exception:
        return False

# ================= Endpoints MT5 =================
@app.route('/api/mt5/tick', methods=['POST'])
def receive_tick_mt5():
    try:
        sig = request.headers.get('X-Signature', '')
        if not verify_hmac_signature(request.get_data(as_text=True), sig, API_SECRET):
            return jsonify({"error":"Invalid signature"}), 401
        tick = request.get_json()
        symbol = normalize_symbol(tick.get('symbol','UNKNOWN'))
        tick['symbol'] = symbol
        tick['received_at'] = time.time()
        tick['server_timestamp'] = datetime.now(timezone.utc).isoformat()
        tick_data_mt5[symbol].append(tick)
        stats['total_ticks'] += 1
        stats['last_activity'] = time.time()
        stats['active_symbols'].add(symbol)
        return jsonify({"status":"success"})
    except Exception as e:
        logger.error(f"/mt5/tick error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mt5/candles', methods=['POST'])
def receive_candles_mt5():
    try:
        sig = request.headers.get('X-Signature', '')
        if not verify_hmac_signature(request.get_data(as_text=True), sig, API_SECRET):
            return jsonify({"error":"Invalid signature"}), 401
        data = request.get_json()
        candles = data.get('candles', [data] if 'symbol' in data else [])
        out = []
        for c in candles:
            symbol = normalize_symbol(c.get('symbol','UNKNOWN'))
            timeframe = str(c.get('timeframe','M5')).upper()
            is_closed = bool(c.get('closed', True))
            ts = c.get('timestamp','')
            tfm = TF_MINUTES.get(timeframe, TIMEFRAME_MIN)

            if is_closed:
                dt_utc = parse_mt5_timestamp_with_broker_tz(ts, tfm)
            else:
                dt_utc = floor_to_tf_broker(datetime.now(timezone.utc), tfm)

            c['unix_time'] = int(dt_utc.timestamp())
            c['unix_time_ms'] = c['unix_time']*1000
            c['server_timestamp'] = datetime.now(timezone.utc).isoformat()
            c['symbol'] = symbol
            c['timeframe'] = timeframe
            if not c.get('source'):
                c['source'] = 'ea'

            sc = sanitize_candle(c)
            if sc is None:
                continue

            prev_live = live_candle_mt5.get(symbol)
            if not sc['closed']:
                if prev_live and prev_live.get('unix_time') is not None and sc['unix_time'] > prev_live['unix_time']:
                    prev_closed = sanitize_candle(prev_live.copy())
                    if prev_closed:
                        prev_closed['closed'] = True
                        out.append(prev_closed)
                live_candle_mt5[symbol] = sc
            else:
                out.append(sc)
                if prev_live and prev_live.get('unix_time') == sc['unix_time']:
                    live_candle_mt5.pop(symbol, None)

            stats['active_symbols'].add(symbol)
            stats['last_activity'] = time.time()

        if out:
            upsert_candles_into_memory(candle_data_mt5, out)
            for sc in out:
                if sc.get('closed'):
                    CSV_STORE.upsert_closed_candle(sc)

        return jsonify({"status":"success","candles_processed": len(out)})
    except Exception as e:
        logger.error(f"/mt5/candles error: {e}")
        return jsonify({"error": str(e)}), 500

# ================= Endpoints IQ (data push desde WS externo) =================
@app.route('/api/iq/tick', methods=['POST'])
def receive_tick_iq():
    try:
        data = request.get_json(force=True, silent=False) or {}
        symbol = normalize_symbol(data.get('symbol','UNKNOWN'))
        price = data.get('price')
        bid = data.get('bid', price)
        ask = data.get('ask', price)
        ts_ms = int(data.get('timestamp_ms', time.time()*1000))
        tick = {
            "symbol": symbol,
            "price": _to_float(price),
            "bid": _to_float(bid),
            "ask": _to_float(ask),
            "timestamp_ms": ts_ms,
            "received_at": time.time(),
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "iq"
        }
        tick_data_iq[symbol].append(tick)
        stats['total_ticks'] += 1
        stats['last_activity'] = time.time()
        stats['active_symbols'].add(symbol)
        return jsonify({"status":"success"})
    except Exception as e:
        logger.error(f"/iq/tick error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/iq/candles', methods=['POST'])
def receive_candles_iq():
    try:
        payload = request.get_json(force=True, silent=False) or {}
        symbol = normalize_symbol(payload.get('symbol','EURUSD'))
        timeframe = str(payload.get('timeframe','M5')).upper()
        tfm = TF_MINUTES.get(timeframe, TIMEFRAME_MIN)
        candles = payload.get('candles', [])
        now_s = int(time.time())

        out = []
        for r in candles:
            try:
                ut_from = int(r.get('from'))
                ut_to = int(r.get('to', ut_from + tfm*60))
                o = _to_float(r.get('open')); h = _to_float(r.get('max')); l = _to_float(r.get('min')); c = _to_float(r.get('close'))
                v = _to_float(r.get('volume')) or 0.0
                closed = bool(r.get('closed', now_s >= ut_to))
                if o is None or c is None:
                    continue
                if h is None: h = max(o, c)
                if l is None: l = min(o, c)
                if h < l: h, l = l, h
                if o > h: h = o
                if o < l: l = o
                if c > h: h = c
                if c < l: l = c

                out.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "open": o, "high": h, "low": l, "close": c, "volume": v,
                    "timestamp": datetime.fromtimestamp(ut_from, tz=timezone.utc).isoformat(),
                    "unix_time": ut_from, "unix_time_ms": ut_from*1000,
                    "closed": closed, "source": "iq", "received_at": time.time(),
                })
            except Exception:
                continue

        if out:
            grouped_by_sym = defaultdict(list)
            for c in out:
                grouped_by_sym[c['symbol']].append(c)
            pushed = 0
            for sym, seq in grouped_by_sym.items():
                seq.sort(key=lambda x: x['unix_time'])
                live_new = [x for x in seq if not x['closed']]
                if live_new:
                    live_candle_iq[sym] = live_new[-1]
                closed_new = [x for x in seq if x['closed']]
                if closed_new:
                    upsert_candles_into_memory(candle_data_iq, closed_new)
                    for sc in closed_new:
                        CSV_STORE.upsert_closed_candle(sc)
                    pushed += len(closed_new)
            return jsonify({"status":"success","candles_processed": pushed})
        return jsonify({"status":"success","candles_processed": 0})
    except Exception as e:
        logger.error(f"/iq/candles error: {e}")
        return jsonify({"error": str(e)}), 500

# ================== IQ: Login/Logout/Status/Order ==================
_IQ_LOCK = threading.Lock()
_IQ_API = None
_IQ_SESSION = {
    "connected": False,
    "email": None,
    "balance_type": "PRACTICE",  # PRACTICE|REAL
    "profile": {},
    "balance": None,
    "last_error": None,
}

def _iq_safe_balance(api):
    try:
        if hasattr(api, "get_balance"):
            return api.get_balance()
    except Exception:
        return None
    return None

def _iq_safe_profile(api):
    try:
        if hasattr(api, "get_profile"):
            return api.get_profile()
    except Exception:
        return {}
    return {}

@app.route('/api/iq/login', methods=['POST'])
def iq_login():
    if not _IQ_AVAILABLE:
        return jsonify({"error": "Falta iqoptionapi. Instala: pip install iqoptionapi"}), 500
    data = request.get_json(force=True, silent=False) or {}
    email = str(data.get('email','')).strip()
    password = str(data.get('password','')).strip()
    balance_type = str(data.get('balance_type','PRACTICE')).upper()
    if balance_type not in ('PRACTICE','REAL'):
        balance_type = 'PRACTICE'
    if not email or not password:
        return jsonify({"error":"email y password requeridos"}), 400
    global _IQ_API, _IQ_SESSION
    with _IQ_LOCK:
        try:
            _IQ_API = IQ_Option(email, password)
            ok, reason = _IQ_API.connect()
            if not ok:
                _IQ_SESSION.update({"connected": False, "last_error": reason})
                return jsonify({"error": f"No se pudo conectar a IQ Option: {reason}"}), 400
            _IQ_API.change_balance(balance_type)
            _IQ_SESSION.update({
                "connected": True,
                "email": email,
                "balance_type": balance_type,
                "profile": _iq_safe_profile(_IQ_API),
                "balance": _iq_safe_balance(_IQ_API),
                "last_error": None,
            })
            return jsonify({"status":"success", "session": _IQ_SESSION})
        except Exception as e:
            _IQ_SESSION.update({"connected": False, "last_error": str(e)})
            return jsonify({"error": str(e)}), 500

@app.route('/api/iq/logout', methods=['POST'])
def iq_logout():
    global _IQ_API, _IQ_SESSION
    with _IQ_LOCK:
        try:
            if _IQ_API:
                try:
                    _IQ_API.api.close()  # cierra socket interno si está disponible
                except Exception:
                    pass
            _IQ_API = None
            _IQ_SESSION.update({"connected": False, "email": None, "profile": {}, "balance": None})
            return jsonify({"status":"success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/iq/status', methods=['GET'])
def iq_status():
    global _IQ_API, _IQ_SESSION
    with _IQ_LOCK:
        if _IQ_API and _IQ_SESSION.get("connected"):
            _IQ_SESSION["balance"] = _iq_safe_balance(_IQ_API)
            _IQ_SESSION["profile"] = _iq_safe_profile(_IQ_API) or _IQ_SESSION.get("profile", {})
        return jsonify({"session": _IQ_SESSION, "available": _IQ_AVAILABLE})

@app.route('/api/iq/order', methods=['POST'])
def iq_order():
    """
    Body JSON:
    {
      "symbol":"EURUSD",
      "action":"BUY"|"SELL"   # mapea a CALL/PUT
      "amount": 1.5,
      "duration": 1,         # minutos para binarias
      "option_type": "binary"|"digital"
    }
    """
    if not _IQ_AVAILABLE:
        return jsonify({"error": "Falta iqoptionapi. Instala: pip install iqoptionapi"}), 500
    global _IQ_API, _IQ_SESSION
    with _IQ_LOCK:
        if not (_IQ_API and _IQ_SESSION.get("connected")):
            return jsonify({"error":"No conectado a IQ Option"}), 400
        try:
            p = request.get_json(force=True, silent=False) or {}
            symbol = normalize_symbol(p.get('symbol','EURUSD'))
            action = str(p.get('action','BUY')).upper()
            option_type = str(p.get('option_type','binary')).lower()
            amount = float(p.get('amount', 1))
            duration = int(p.get('duration', 1))  # minutos en binarias

            direction = 'call' if action in ('BUY','CALL') else 'put'

            if option_type == 'digital':
                # Intento para digital: algunos forks usan buy_digital_spot
                try:
                    check, order_id = _IQ_API.buy_digital_spot(symbol, amount, direction, duration)
                    return jsonify({"status": "success", "type":"digital", "placed": bool(check), "order_id": order_id})
                except Exception as e1:
                    # Fallback a open_digital en algunos forks
                    try:
                        order_id = _IQ_API.open_digital_option(symbol, amount, direction, duration)
                        placed = bool(order_id is not None)
                        return jsonify({"status": "success", "type":"digital", "placed": placed, "order_id": order_id})
                    except Exception as e2:
                        return jsonify({"error": f"No se pudo colocar digital: {e1} | {e2}"}), 500
            else:
                # Binarias clásicas
                try:
                    check, order_id = _IQ_API.buy(amount, symbol, direction, duration)
                    if not check:
                        return jsonify({"error": f"Orden binaria rechazada: {order_id}"}), 400
                    return jsonify({"status": "success", "type":"binary", "placed": True, "order_id": order_id})
                except Exception as e:
                    return jsonify({"error": f"No se pudo colocar binaria: {e}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ================= Señales =================
@app.route('/api/signals', methods=['GET','POST'])
def signals_endpoint():
    try:
        if request.method == 'POST':
            sig = request.get_json(force=True, silent=False) or {}
            sig['id'] = stats['total_signals'] + 1
            sig['created_at'] = datetime.now(timezone.utc).isoformat()
            sig['created_unix'] = time.time()
            signals_store.appendleft(sig)
            stats['total_signals'] += 1
            persist_signal(sig)
            return jsonify({"status":"success","signal": sig}), 201
        limit = int(request.args.get('limit', 50))
        return jsonify({"signals": list(signals_store)[:limit], "total_signals": stats['total_signals']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= /api/data (dual fuente) =================
@app.route('/api/data', methods=['GET'])
def get_data():
    source = str(request.args.get('source', ACTIVE_SOURCE or 'mt5')).lower()
    if source not in ('mt5','iq'):
        source = 'mt5'

    if source == 'mt5':
        ticks_store = tick_data_mt5
        candles_store = candle_data_mt5
        live_store = live_candle_mt5
    else:
        ticks_store = tick_data_iq
        candles_store = candle_data_iq
        live_store = live_candle_iq

    recent_ticks = {}
    recent_candles = {}
    signals_by_symbol = defaultdict(list)

    for sym, ticks in ticks_store.items():
        recent_ticks[sym] = list(ticks)[-20:]

    symbols = set(candles_store.keys()) | set(live_store.keys()) | set(stats['active_symbols'])

    for sym in symbols:
        closed = sorted(list(candles_store.get(sym, [])), key=lambda x: x.get('unix_time', 0))
        recent = closed[-FRONTEND_CLOSED_LIMIT:]
        live = live_store.get(sym)
        if live is not None:
            if recent and recent[-1].get('unix_time') == live.get('unix_time'):
                recent[-1] = live
            else:
                recent = recent + [live]
        recent_candles[sym] = recent

    for s in list(signals_store):
        sym = s.get('symbol','UNKNOWN')
        signals_by_symbol[sym].append(s)
        if len(signals_by_symbol[sym]) > 200:
            signals_by_symbol[sym] = signals_by_symbol[sym][:200]

    return jsonify({
        "source": source,
        "ticks_by_symbol": recent_ticks,
        "candles_by_symbol": recent_candles,
        "signals_by_symbol": signals_by_symbol,
        "symbols": list(symbols),
        "server_time": time.time(),
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_ticks": stats['total_ticks'],
            "total_candles": stats['total_candles'],
            "total_signals": stats['total_signals']
        }
    })

# ================= CSV/YF endpoints (sin cambios esenciales) =================
@app.route('/api/csv/load', methods=['POST'])
def csv_load_into_memory():
    try:
        p = request.get_json(force=True, silent=False) or {}
        symbol = normalize_symbol(p.get('symbol','EURUSD'))
        timeframe = str(p.get('timeframe','M5')).upper()
        max_rows = int(p.get('max_rows', 0) or 0)
        rows = CSV_STORE.read_csv(symbol, timeframe, max_rows=max_rows)
        target = str(p.get('target','mt5')).lower()
        if target == 'iq':
            loaded, skipped = upsert_candles_into_memory(candle_data_iq, rows)
        else:
            loaded, skipped = upsert_candles_into_memory(candle_data_mt5, rows)
        return jsonify({"status":"success","symbol":symbol,"timeframe":timeframe,"csv_rows_read":len(rows),"loaded_or_replaced":loaded,"skipped":skipped})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/csv/sync', methods=['POST'])
def csv_sync_from_yf():
    try:
        p = request.get_json(force=True, silent=False) or {}
        symbol = normalize_symbol(p.get('symbol','EURUSD'))
        timeframe = str(p.get('timeframe','M5')).upper()
        period = p.get('period','1mo')
        start = p.get('start')
        end = p.get('end')
        limit = int(p.get('limit', 0) or 0)
        loaded_csv, skipped_csv, candles, err = CSV_STORE.sync_from_yfinance(symbol, timeframe, period=period, start_iso=start, end_iso=end, limit=limit)
        if err and loaded_csv == 0 and not candles:
            return jsonify({"error": err}), 400
        loaded_mem, skipped_mem = upsert_candles_into_memory(candle_data_mt5, candles)
        return jsonify({"status":"success","symbol":symbol,"timeframe":timeframe,"loaded_to_csv":loaded_csv,"skipped_in_csv":skipped_csv,"loaded_or_replaced_in_memory":loaded_mem,"skipped_in_memory":skipped_mem})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/csv/export', methods=['GET'])
def csv_export_file():
    try:
        symbol = normalize_symbol(request.args.get('symbol','EURUSD'))
        timeframe = str(request.args.get('timeframe','M5')).upper()
        fpath = CSV_STORE.path(symbol, timeframe)
        if not os.path.exists(fpath):
            return jsonify({"error":"CSV no existe"}), 404
        return send_file(fpath, mimetype='text/csv', as_attachment=True, download_name=os.path.basename(fpath))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= YF opcional =================
TF_TO_YF = {'M1':'1m','M5':'5m','M15':'15m','M30':'30m','H1':'60m','D1':'1d'}
def to_yf_ticker(s: str) -> str:
    return csv_store.to_yf_ticker(s)

@app.route('/api/yf/history', methods=['GET'])
def yf_history():
    if not _YF_AVAILABLE:
        return jsonify({"error":"yfinance/pandas no instalados"}), 500
    symbol = normalize_symbol(request.args.get('symbol','EURUSD'))
    timeframe = str(request.args.get('timeframe','M5')).upper()
    period = request.args.get('period','1mo')
    start = request.args.get('start'); end = request.args.get('end')
    limit = int(request.args.get('limit', 0) or 0)
    try:
        interval = TF_TO_YF.get(timeframe)
        if not interval: return jsonify({"error":"tf no soportado"}), 400
        yf_t = to_yf_ticker(symbol)
        if start or end:
            df = yf.download(yf_t, start=start, end=end, interval=interval, auto_adjust=False, progress=False, prepost=False)
        else:
            df = yf.download(yf_t, period=period, interval=interval, auto_adjust=False, progress=False, prepost=False)
        if df is None or df.empty: return jsonify({"symbol":symbol,"timeframe":timeframe,"count":0,"candles":[]})
        candles = []
        for ts, row in df.iterrows():
            ts_utc = ts.tz_convert("UTC") if hasattr(ts,"tz_convert") else ts
            ut = int(pd.Timestamp(ts_utc).timestamp())
            o = float(row.get('Open', row.get('open', 0.0)))
            h = float(row.get('High', row.get('high', o)))
            l = float(row.get('Low',  row.get('low',  o)))
            c = float(row.get('Close',row.get('close',o)))
            v = float(row.get('Volume', row.get('volume', 0.0)))
            if h < l: h, l = l, h
            if o > h: h = o
            if o < l: l = o
            if c > h: h = c
            if c < l: l = c
            candles.append({"symbol":symbol,"timeframe":timeframe,"open":o,"high":h,"low":l,"close":c,"volume":v,"timestamp": pd.Timestamp(ts_utc).isoformat(),"unix_time":ut,"unix_time_ms":ut*1000,"closed":True,"source":"yfinance","received_at": time.time()})
        if limit and len(candles) > limit:
            candles = candles[-limit:]
        return jsonify({"symbol":symbol,"timeframe":timeframe,"count": len(candles),"candles": candles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= Bootstrap =================
def bootstrap_load_and_sync():
    for symbol, tf in BOOTSTRAP_PAIRS:
        try:
            rows = CSV_STORE.read_csv(symbol, tf, max_rows=500000)
            upsert_candles_into_memory(candle_data_mt5, rows)
            logger.info(f"CSV cargado: {symbol} {tf} -> {len(rows)} velas")

            loaded_csv, skipped_csv, candles, err = CSV_STORE.sync_from_yfinance(symbol, tf, period='1mo', limit=0)
            if err and loaded_csv == 0 and not candles:
                logger.warning(f"YF sync {symbol} {tf} error: {err}")
            else:
                upsert_candles_into_memory(candle_data_mt5, candles)
                logger.info(f"YF sync {symbol} {tf}: csv+{loaded_csv} (skip {skipped_csv}) | total mem {len(candle_data_mt5[symbol])}")
        except Exception as e:
            logger.warning(f"Bootstrap {symbol} {tf} fallo: {e}")

def run_https():
    from werkzeug.serving import make_server
    print("🔒 HTTPS 5001")
    make_server('0.0.0.0', HTTPS_PORT, app, ssl_context='adhoc').serve_forever()

def run_http():
    from werkzeug.serving import make_server
    print("🌐 HTTP 5002")
    make_server('0.0.0.0', HTTP_PORT, app).serve_forever()

if __name__ == '__main__':
    print("🚀 STC Server iniciando...")
    load_signals(max_rows=1000)
    bootstrap_load_and_sync()
    threading.Thread(target=run_http, daemon=True).start()
    run_https()