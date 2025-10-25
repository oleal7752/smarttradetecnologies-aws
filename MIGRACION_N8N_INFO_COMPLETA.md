# 📋 INFORMACIÓN COMPLETA DEL PROYECTO STC PARA MIGRACIÓN A N8N

## 🎯 RESUMEN EJECUTIVO (2 líneas)

**Sistema SaaS multi-tenant de señales de trading para opciones binarias que obtiene datos de Twelve Data API (EUR/USD, GBP/USD, USD/JPY, AUD/USD) cada 5 minutos, calcula 8 estrategias (RSI, MACD, Bollinger, Estocástico, ADX, CCI, Williams %R, MFI), genera señales CALL/PUT con Martingale automático, sincronización temporal <10ms, y las envía en tiempo real vía WebSocket a múltiples usuarios simultáneos con acceso controlado por códigos promocionales.**

---

## 1️⃣ ARQUITECTURA Y FUNCIONALIDAD

### 📌 ¿Qué hace el proyecto?

- **Bot de Trading Multi-Estrategia**: 8 estrategias simultáneas
- **Señales en Tiempo Real**: CALL/PUT para opciones binarias
- **Martingale Automático**: Sistema dual (CALL y PUT independientes)
- **Multi-Tenant SaaS**: Múltiples usuarios con suscripciones
- **Copy Trading Visual**: Dashboard glassmorphism 3D con señales en tiempo real

### 📌 ¿Qué datos procesa?

**Fuentes de Datos:**
- **API Principal**: Twelve Data (forex real-time, $300/mes)
- **API Secundaria**: IQ Option (trading execution)
- **Fallback**: YFinance (datos históricos)

**Pares Operados:**
- EUR/USD (principal)
- GBP/USD
- USD/JPY
- AUD/USD

**Timeframe:**
- **M5 (5 minutos)** - FIJO, no configurable
- Actualización cada 300 segundos exactos
- Sincronización temporal estricta (<10ms)

### 📌 ¿Cómo genera señales?

**8 Estrategias (Reglas Fijas):**

1. **RSI Bounce** (ID: rsi_bounce)
   - RSI < 30 → CALL
   - RSI > 70 → PUT
   - Validation: Color de vela debe coincidir

2. **MACD Crossover** (ID: macd_crossover)
   - MACD cruza por encima de Signal → CALL
   - MACD cruza por debajo de Signal → PUT

3. **Bollinger Squeeze** (ID: bollinger_squeeze)
   - Precio toca banda inferior → CALL
   - Precio toca banda superior → PUT

4. **Stochastic Oversold** (ID: stochastic_oversold)
   - %K < 20 → CALL
   - %K > 80 → PUT

5. **ADX Trend** (ID: adx_trend)
   - ADX > 25 + DI+ > DI- → CALL
   - ADX > 25 + DI- > DI+ → PUT

6. **CCI Extreme** (ID: cci_extreme)
   - CCI < -100 → CALL
   - CCI > 100 → PUT

7. **Williams %R** (ID: williams_r)
   - Williams %R < -80 → CALL
   - Williams %R > -20 → PUT

8. **MFI Divergence** (ID: mfi_divergence)
   - MFI < 20 → CALL
   - MFI > 80 → PUT

**Validación Estricta:**
- Color de vela DEBE coincidir con señal
- Verificación temporal precisa
- Confirmación de cierre de vela M5

**Lógica de Martingale:**
- Verifica resultado al cierre de vela M5
- Si pérdida → inicia Gale 1 (monto x2)
- Si pérdida en Gale 1 → Gale 2 (monto x4)
- Si pérdida en Gale 2 → STOP y reinicia

---

## 2️⃣ ESTRUCTURA DE ARCHIVOS

### 📁 Archivos Principales:

**BACKEND (Flask - Puerto 5002):**
```
iq_routes_redis_patch.py        # API REST con MemoryRedis
├── GET /api/v1/candles          # Datos de velas
├── GET /api/v2/candles          # Datos optimizados
├── GET /api/symbols             # Lista de pares
├── GET /api/user_balance        # Balance IQ Option
└── POST /api/broker_accounts    # Gestión de cuentas

database.py                      # SQLAlchemy models
├── users, broker_accounts
├── subscriptions, promo_codes
├── bots, bot_stats, trades
└── candles (OHLCV data)
```

**DASHBOARD (Flask - Puerto 5000):**
```
dashboard_server.py              # Servidor principal + WebSocket proxy
├── /login, /register            # Auth routes
├── /signals                     # Panel de señales
├── /welcome                     # Bienvenida post-código
├── /access-validation           # Validación de acceso
└── WebSocket proxy → :8000      # Proxy a RealTime Server
```

**REALTIME (FastAPI - Puerto 8000):**
```
start_realtime_server.py         # WebSocket server
├── /ws/signals/{user_id}        # Canal WebSocket por usuario
├── Envía señales cada 300s      # Sincronizado con velas M5
└── Broadcast multi-tenant       # Aislamiento por user_id
```

**SERVICIOS CORE:**
```
strategy_engine.py               # Motor de estrategias
├── calculate_rsi_bounce()
├── calculate_macd_crossover()
├── calculate_bollinger_squeeze()
├── calculate_stochastic_oversold()
├── calculate_adx_trend()
├── calculate_cci_extreme()
├── calculate_williams_r()
└── calculate_mfi_divergence()

dual_gale_manager.py             # Sistema Martingale dual
├── verify_result()              # Verifica win/loss
├── initiate_gale()              # Inicia Martingale
├── reset_sequence()             # Resetea al ganar
└── Maneja CALL y PUT separados

candles_store.py                 # Caché de velas
├── fetch_from_twelvedata()      # API Twelve Data
├── fetch_from_yfinance()        # Fallback histórico
└── store_in_postgresql()        # Almacena en BD
```

**INICIALIZACIÓN:**
```
populate_production.py           # Setup automático
├── Crea admin (admin@stc.com / admin123)
├── Crea 8 bots (1 por estrategia)
└── Ejecuta al desplegar

start_system.py                  # Orquestador principal
├── Inicia Dashboard (:5000)
├── Inicia Backend (:5002)
├── Inicia RealTime (:8000)
└── Ejecuta candles_store en loop
```

**AUTENTICACIÓN:**
```
auth_routes.py                   # Sistema de auth
├── /auth/register               # Registro + email verification
├── /auth/verify/<token>         # Verificación de email
├── /auth/login                  # Login + sesión
└── /auth/logout                 # Logout

email_service.py                 # Envío de emails
└── send_verification_email()    # Gmail SMTP
```

**ADMIN:**
```
admin_routes.py                  # Panel admin
├── /admin/users                 # Gestión usuarios
├── /admin/promo-codes           # Códigos promocionales
├── /admin/bots                  # Control de bots
└── /admin/pricing               # Configuración precios
```

### 📁 Frontend:

```
templates/
├── login.html                   # Login
├── register.html                # Registro
├── verify_email.html            # Verificación
├── access_validation.html       # Módulo de código
├── welcome.html                 # Bienvenida
├── signals.html                 # Panel de señales 3D
├── dashboard.html               # Dashboard principal
└── admin/                       # Panel admin

static/
├── css/
│   └── glassmorphism-3d.css    # Estilos 3D espaciales
└── js/
    ├── signals-websocket.js     # WebSocket client
    └── chart-realtime.js        # Chart.js integration
```

---

## 3️⃣ DEPENDENCIAS Y SERVICIOS

### 🔧 Lenguaje Principal:
**Python 3.11**

### 🔧 Librerías Principales:

```python
# Web Frameworks
Flask==3.0.0
FastAPI==0.104.1
uvicorn==0.24.0

# Database
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9

# Trading & Data
iqoptionapi==4.5.1
yfinance==0.2.31
pandas==2.1.3
numpy==1.26.2

# Technical Indicators
ta==0.11.0                       # RSI, MACD, Bollinger, etc.

# Communication
websockets==12.0
requests==2.31.0

# Utils
python-dotenv==1.0.0
werkzeug==3.0.1                  # Password hashing
```

### 🔧 APIs que usa:

**Principal:**
- **Twelve Data API** (forex real-time)
  - Endpoint: `https://api.twelvedata.com/time_series`
  - Método: GET
  - Params: `symbol=EUR/USD&interval=5min&apikey=XXX`
  - Costo: $300/mes

**Trading:**
- **IQ Option API** (iqoptionapi)
  - Login/logout
  - Balance checking
  - Trade execution

**Comunicación:**
- **Gmail SMTP** (verificación de email)
  - SMTP: smtp.gmail.com:587
  - TLS enabled

**Fallback:**
- **YFinance** (datos históricos)

---

## 4️⃣ BASE DE DATOS

### 💾 PostgreSQL (Producción)

**Schema Principal:**

```sql
-- USUARIOS Y AUTH
users
├── id (serial PK)
├── email (unique)
├── password_hash
├── email_verified (boolean)
├── verification_token
└── created_at

-- CUENTAS BROKER
broker_accounts
├── id (serial PK)
├── user_id (FK → users)
├── broker_type (iq_option)
├── email
├── password_encrypted
├── balance_type (PRACTICE/REAL)
└── is_connected (boolean)

-- SUSCRIPCIONES
subscriptions
├── id (serial PK)
├── user_id (FK → users)
├── plan_type
├── start_date
├── end_date
├── is_active (boolean)
└── auto_renew

-- CÓDIGOS PROMOCIONALES
promo_codes
├── id (serial PK)
├── code (unique)
├── type (reseller/agent/courtesy)
├── duration_days
├── is_active
├── uses_count
└── max_uses

-- BOTS
bots
├── id (serial PK)
├── user_id (FK → users)
├── strategy_name (rsi_bounce, macd_crossover, etc.)
├── symbol (EURUSD, GBPUSD, etc.)
├── timeframe (M5)
├── investment_amount
├── is_active (boolean)
├── gale_enabled (boolean)
└── max_gale_level (2)

-- ESTADÍSTICAS DE BOTS
bot_stats
├── id (serial PK)
├── bot_id (FK → bots)
├── total_trades
├── wins
├── losses
├── win_rate
├── profit_loss
└── last_updated

-- TRADES
trades
├── id (serial PK)
├── bot_id (FK → bots)
├── symbol
├── direction (CALL/PUT)
├── entry_price
├── exit_price
├── investment
├── payout
├── result (WIN/LOSS)
├── gale_level (0/1/2)
└── executed_at

-- VELAS (OHLCV)
candles
├── id (serial PK)
├── symbol (EURUSD, etc.)
├── timeframe (M5)
├── timestamp (unique per symbol/timeframe)
├── open
├── high
├── low
├── close
├── volume
└── source (twelvedata/yfinance)
```

**Índices Críticos:**
```sql
CREATE INDEX idx_candles_symbol_time ON candles(symbol, timeframe, timestamp DESC);
CREATE INDEX idx_trades_bot_time ON trades(bot_id, executed_at DESC);
CREATE INDEX idx_bots_user_active ON bots(user_id, is_active);
```

---

## 5️⃣ AUTOMATIZACIÓN

### ⏰ ¿Cómo se ejecuta?

**Loop Infinito con Sincronización Temporal:**

```python
# En start_system.py
while True:
    current_time = get_server_time()  # UTC
    
    # Espera hasta próximo M5 exacto
    seconds_until_next_m5 = 300 - (current_time % 300)
    sleep(seconds_until_next_m5)
    
    # Ejecuta en el segundo exacto
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']:
        fetch_and_store_candle(symbol, 'M5')
        
        # Genera señales para bots activos
        active_bots = get_active_bots(symbol)
        for bot in active_bots:
            signal = strategy_engine.calculate(bot)
            if signal:
                broadcast_via_websocket(signal)
```

### ⏰ Frecuencia:

- **Candles**: Cada 300 segundos exactos (M5)
- **Señales**: Al cierre de cada vela M5
- **WebSocket**: Broadcast inmediato (<10ms)
- **Martingale**: Verificación al siguiente cierre M5
- **Balance Check**: Cada trade

---

## 6️⃣ CONFIGURACIÓN (.env)

```bash
# DATABASE
DATABASE_URL=postgresql://user:pass@host:5432/stc_production

# TWELVE DATA API
TWELVEDATA_API_KEY=tu_api_key_aqui

# IQ OPTION
IQ_EMAIL=tu_email@example.com
IQ_PASSWORD=tu_password
IQ_BALANCE_TYPE=PRACTICE

# EMAIL SERVICE
GMAIL_USER=tu_gmail@gmail.com
GMAIL_APP_PASSWORD=tu_app_password

# OTROS
FINNHUB_API_KEY=opcional
BOT_API_KEY=opcional

# URLS (auto en producción)
BACKEND_API_URL=http://localhost:5002
REALTIME_API_URL=http://localhost:8000
REALTIME_WS_URL=ws://localhost:8000
```

---

## 7️⃣ FLUJO DE DATOS COMPLETO

```
1. INICIO (cada 300s exactos)
   └─> Twelve Data API: GET EUR/USD M5
       └─> Respuesta: OHLCV data
           └─> Almacena en PostgreSQL (tabla candles)

2. CÁLCULO DE SEÑALES (inmediato)
   └─> Strategy Engine: calcula 8 estrategias
       └─> RSI, MACD, Bollinger, Stochastic...
           └─> Genera señal CALL o PUT
               └─> Valida color de vela

3. BROADCAST (< 10ms)
   └─> WebSocket Server (:8000)
       └─> Envía a usuarios conectados
           └─> Filtro por user_id + acceso activo
               └─> Cliente recibe señal en tiempo real

4. EJECUCIÓN (opcional - auto trading)
   └─> Si bot.auto_execute = True
       └─> IQ Option API: ejecuta trade
           └─> Almacena en tabla trades
               └─> Actualiza bot_stats

5. VERIFICACIÓN MARTINGALE (próximo M5)
   └─> Dual Gale Manager
       └─> Verifica resultado (WIN/LOSS)
           └─> Si LOSS → inicia Gale
           └─> Si WIN → resetea secuencia

6. PERSISTENCIA
   └─> PostgreSQL: candles, trades, bot_stats
   └─> MemoryRedis: caché de datos recientes
```

---

## 8️⃣ ENDPOINTS CRÍTICOS PARA N8N

### API REST (Puerto 5002):

```
GET /api/v2/candles
├─ Params: symbol, timeframe, limit
├─ Response: [{timestamp, open, high, low, close, volume}]
└─ Cache: MemoryRedis (60s TTL)

GET /api/symbols
├─ Response: [EURUSD, GBPUSD, USDJPY, AUDUSD]

GET /api/user_balance
├─ Headers: Authorization: Bearer {token}
├─ Response: {balance, currency, type}

POST /api/execute_trade
├─ Body: {symbol, direction, amount, gale_level}
├─ Response: {trade_id, status, result}
```

### WebSocket (Puerto 8000):

```
WS /ws/signals/{user_id}
├─ Connect: wss://domain:8000/ws/signals/123
├─ Receive: {
│     type: "signal",
│     symbol: "EURUSD",
│     direction: "CALL",
│     strategy: "rsi_bounce",
│     confidence: 85,
│     timestamp: 1699876543,
│     server_time: "2024-10-11T15:30:00Z",
│     indicators: {rsi: 28, macd: -0.0012, ...}
│   }
└─ Ping/Pong: cada 30s
```

---

## 9️⃣ ARCHIVOS PRINCIPALES (CÓDIGO)

### start_system.py
```python
import multiprocessing
from dashboard_server import run_dashboard
from iq_routes_redis_patch import run_backend
from start_realtime_server import run_realtime
from candles_store import continuous_candle_update

if __name__ == "__main__":
    processes = [
        multiprocessing.Process(target=run_dashboard, args=(5000,)),
        multiprocessing.Process(target=run_backend, args=(5002,)),
        multiprocessing.Process(target=run_realtime, args=(8000,)),
        multiprocessing.Process(target=continuous_candle_update)
    ]
    
    for p in processes:
        p.start()
    
    for p in processes:
        p.join()
```

### strategy_engine.py (extracto)
```python
def calculate_rsi_bounce(candles):
    df = pd.DataFrame(candles)
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    
    last_rsi = df['rsi'].iloc[-1]
    last_candle_color = 'green' if df['close'].iloc[-1] > df['open'].iloc[-1] else 'red'
    
    if last_rsi < 30 and last_candle_color == 'green':
        return {'direction': 'CALL', 'confidence': 85, 'rsi': last_rsi}
    elif last_rsi > 70 and last_candle_color == 'red':
        return {'direction': 'PUT', 'confidence': 85, 'rsi': last_rsi}
    
    return None
```

---

## 🔟 CREDENCIALES DE ADMIN (AUTO-CREADAS)

```
Email: admin@stc.com
Password: admin123
Role: superadmin
```

---

## 🎯 PUNTOS CLAVE PARA N8N

1. **Timing es CRÍTICO**: Sincronización exacta con velas M5
2. **Multi-Tenant**: Filtrar señales por user_id
3. **Validación Estricta**: Color de vela + indicadores
4. **Martingale Dual**: CALL y PUT independientes
5. **WebSocket Required**: Para latencia <10ms
6. **PostgreSQL**: Almacén único de datos
7. **Twelve Data API**: Fuente principal de datos ($300/mes)
8. **8 Estrategias Paralelas**: Todas se calculan simultáneamente

---

## 📊 VENTAJAS DE MIGRAR A N8N

✅ **Visual Workflow**: Todo el flujo en nodos visuales
✅ **Webhook Nativo**: Twelve Data → n8n automático
✅ **PostgreSQL Directo**: Sin ORM, queries optimizadas
✅ **Cron Jobs Precisos**: Ejecución exacta cada 300s
✅ **Error Handling**: Reintentos automáticos
✅ **Logs Detallados**: Debugging visual completo
✅ **Escalabilidad**: AWS con auto-scaling
✅ **Latencia Ultra-Baja**: <2ms en AWS

---

## 📦 REQUIREMENTS.TXT

```
Flask==3.0.0
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
websockets==12.0
fastapi==0.104.1
uvicorn==0.24.0
yfinance==0.2.31
requests==2.31.0
werkzeug==3.0.1
python-dotenv==1.0.0
iqoptionapi==4.5.1
pandas==2.1.3
numpy==1.26.2
ta==0.11.0
```

---

**✅ INFORMACIÓN COMPLETA LISTA PARA MIGRACIÓN A N8N/AWS**
