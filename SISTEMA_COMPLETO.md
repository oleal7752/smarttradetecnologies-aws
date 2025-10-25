# 📚 SISTEMA COMPLETO - smarttradetecnologies-ar
## Documentación Técnica Detallada para Backup y Migración AWS

---

## 🎯 DESCRIPCIÓN GENERAL DEL SISTEMA

**smarttradetecnologies-ar** es un sistema SaaS multi-tenant de trading automatizado con señales en tiempo real para opciones binarias. Integra IQ Option para ejecución automática de trades usando estrategias avanzadas con sistema de Martingala dual.

### Características Principales
- ✅ **Trading Automatizado**: 8 estrategias avanzadas (RSI, MACD, Bollinger, etc.)
- ✅ **Señales en Tiempo Real**: Análisis M5 vela por vela con WebSockets
- ✅ **Sistema Martingala Dual**: Gestión independiente de secuencias CALL/PUT
- ✅ **Multi-Tenancia**: Cada usuario conecta su propia cuenta de broker
- ✅ **PWA Completo**: Instalable como app nativa con Service Worker
- ✅ **Email Profesional**: Gmail SMTP con verificación obligatoria
- ✅ **Admin Panel**: CRUD completo de usuarios, bots, códigos promo
- ✅ **Backtesting**: Sistema de simulación Monte Carlo con interfaz web

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Stack Tecnológico
```
Frontend:
- HTML5 + CSS3 (Glassmorphism 3D Design)
- JavaScript (Vanilla + Chart.js + Lightweight Charts)
- Bootstrap 5.3.0
- Progressive Web App (PWA)
- Service Worker v3-admin-crud

Backend:
- Python 3.11
- Flask 3.0.0 (Dashboard Server - Port 5000)
- FastAPI 0.104.1 (RealTime Server - Port 8000)
- SQLAlchemy 2.0.23 (ORM)
- PostgreSQL (Neon-backed)

APIs Externas:
- IQ Option API (Trading en tiempo real)
- Twelve Data API (Market data forex)
- YFinance (Data histórica)
- Finnhub API (Market data adicional)

Infraestructura:
- Replit VM (0.5 vCPU / 2 GiB RAM)
- Redis (In-memory cache)
- Gmail SMTP (Email system)
- WebSockets (Real-time communication)
```

---

## 🚀 SERVIDORES Y PROCESOS

### 1. Dashboard Server (Puerto 5000)
**Archivo**: `dashboard_server.py`
**Función**: Servidor principal web + Backend API integrado

**Responsabilidades**:
- Servir interfaz web (templates HTML)
- Autenticación y autorización de usuarios
- API de gestión de bots y suscripciones
- Panel de administración
- Sistema de códigos promocionales
- Gestión de señales visuales

**Blueprints Registrados**:
- `auth_bp` (auth_routes.py) - Autenticación
- `bot_bp` (bot_routes.py) - Gestión de bots
- `admin_bp` (admin_routes.py) - Panel admin

**Endpoints Principales**:
```
/ - Landing page
/auth/login - Login de usuarios
/auth/register - Registro
/auth/verify/<token> - Verificación email
/forgot-password - Recuperación contraseña
/reset-password - Reset contraseña
/trading-charts - Pantalla Venezuela
/charts - Gráficos profesionales
/admin/users - Gestión usuarios (CRUD)
/admin/promo-codes - Códigos promocionales
/admin/bots - Gestión de bots
/api/market/live-candle/<symbol> - Vela en tiempo real
/api/bot/signals - Señales de trading
```

### 2. RealTime Server (Puerto 8000)
**Archivo**: `start_realtime_server.py` → `realtime_trading/realtime_server.py`
**Función**: Servidor FastAPI con WebSockets para datos en tiempo real

**Responsabilidades**:
- WebSocket: `/ws/live` - Stream de velas en tiempo real
- API Status: `/api/status` - Estado del servidor
- Polling cada 3 segundos (optimizado anti-guindar)
- Distribución de datos de mercado a múltiples clientes

### 3. Backend API (Puerto 8080) - INTEGRADO
**Archivo**: `iq_routes_redis_patch.py`
**Función**: API de IQ Option con Redis cache
**NOTA**: En producción, está **integrado** al Dashboard Server

---

## 📁 ESTRUCTURA DE DIRECTORIOS

```
smarttradetecnologies-ar/
│
├── 📂 templates/                    # Plantillas HTML
│   ├── landing.html                # Landing page principal
│   ├── login.html                  # Página de login
│   ├── trading_charts.html         # Pantalla Venezuela
│   ├── forgot_password.html        # Recuperación password
│   ├── reset_password.html         # Reset password
│   ├── dashboard_pro.html          # Dashboard profesional
│   ├── bot_manager.html            # Gestión de bots
│   ├── signals_panel.html          # Panel señales multi-par
│   ├── admin/
│   │   ├── users.html              # CRUD Usuarios
│   │   ├── promo_codes.html        # Códigos promocionales
│   │   ├── bots.html               # Gestión bots admin
│   │   └── strategies.html         # Estrategias de trading
│   └── auth/
│       └── verify_result.html      # Resultado verificación email
│
├── 📂 static/                       # Archivos estáticos
│   ├── sw.js                       # Service Worker PWA v3
│   ├── manifest.json               # PWA Manifest
│   ├── venezuela-flag.jpg          # Bandera Venezuela (8 estrellas)
│   ├── icons/                      # Iconos PWA (8 tamaños)
│   │   ├── icon-72x72.png
│   │   ├── icon-96x96.png
│   │   ├── icon-128x128.png
│   │   ├── icon-144x144.png
│   │   ├── icon-152x152.png
│   │   ├── icon-192x192.png
│   │   ├── icon-384x384.png
│   │   └── icon-512x512.png
│   └── js/
│       ├── stc-charts.js           # Gráficos profesionales
│       ├── lightweight-charts.js   # Librería de gráficos
│       └── dashboard/
│           ├── index.js            # Dashboard principal
│           ├── services/
│           │   └── apiClient.js    # Cliente API
│           ├── components/
│           │   ├── countdownTimer.js
│           │   ├── timeframeSelector.js
│           │   └── symbolSelector.js
│           └── modules/
│               ├── chart.js        # Módulo de gráficos
│               └── state.js        # Gestión de estado
│
├── 📂 realtime_trading/             # Servidor tiempo real
│   └── realtime_server.py          # FastAPI WebSocket server
│
├── 📂 backtest/                     # Sistema de backtesting
│   ├── backtest_server.py          # Servidor Flask backtest
│   ├── backtest_dashboard.html     # Dashboard 3D glassmorphism
│   └── INSTRUCCIONES.md            # Guía de uso
│
├── 📂 services/                     # Servicios del sistema
│   └── candle_service.py           # Servicio de velas
│
├── 📂 docs/                         # Documentación
│   └── GUIA_MIGRACION.html
│
├── 📂 tests/                        # Tests del sistema
│   ├── test_complete_system.py
│   ├── test_iq_connection.py
│   └── test_candles.py
│
├── 🐍 Archivos Python Core:
│   ├── dashboard_server.py         # ⭐ Servidor principal (Port 5000)
│   ├── start_realtime_server.py    # ⭐ Servidor tiempo real (Port 8000)
│   ├── auth_routes.py              # ⭐ Autenticación y autorización
│   ├── bot_routes.py               # ⭐ API de bots
│   ├── admin_routes.py             # ⭐ Panel administración
│   ├── database.py                 # ⭐ Modelos SQLAlchemy
│   ├── email_service.py            # ⭐ Sistema de emails Gmail
│   ├── auto_trading_bot.py         # ⭐ Bot de trading automatizado
│   ├── strategy_engine.py          # ⭐ Motor de estrategias
│   ├── dual_gale_manager.py        # Sistema Martingala dual
│   ├── backtesting_engine.py       # Motor de backtesting
│   ├── candles_store.py            # Almacenamiento de velas
│   ├── iq_client.py                # Cliente IQ Option
│   ├── iq_routes_redis_patch.py    # API IQ Option con Redis
│   ├── memory_redis_server.py      # Servidor Redis en memoria
│   ├── init_admin.py               # ⭐ Inicialización admin
│   ├── populate_production.py      # ⭐ Población datos producción
│   └── start_production.py         # ⭐ Script inicio producción
│
├── 📄 Archivos de Configuración:
│   ├── requirements.txt            # Dependencias Python
│   ├── replit.nix                  # Configuración Nix
│   ├── .replit                     # Config Replit
│   └── pyproject.toml              # Config Python project
│
└── 📚 Documentación:
    ├── replit.md                   # ⭐ Arquitectura y preferencias
    ├── RECUPERACION_CONTRASENA.md  # Sistema password recovery
    ├── ADMIN_CRUD_PRODUCCION.md    # CRUD usuarios troubleshooting
    ├── SISTEMA_COMPLETO.md         # Este archivo
    ├── ARCHIVOS_CRITICOS.txt       # Lista archivos esenciales
    └── BACKUP_AWS.md               # Instrucciones backup AWS
```

---

## 🗄️ BASE DE DATOS POSTGRESQL

### Tablas Principales

#### 1. **users** - Usuarios del sistema
```sql
id SERIAL PRIMARY KEY
email VARCHAR(255) UNIQUE NOT NULL
password_hash VARCHAR(255) NOT NULL
first_name VARCHAR(100)
last_name VARCHAR(100)
country VARCHAR(100)
phone VARCHAR(50)
dni VARCHAR(50) UNIQUE
is_active BOOLEAN DEFAULT TRUE
is_admin BOOLEAN DEFAULT FALSE
is_email_verified BOOLEAN DEFAULT FALSE
email_verification_token VARCHAR(255)
created_at TIMESTAMP DEFAULT NOW()
last_login TIMESTAMP
```

#### 2. **password_resets** - Recuperación de contraseña
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
token VARCHAR(255) UNIQUE NOT NULL
expires_at TIMESTAMP NOT NULL
used BOOLEAN DEFAULT FALSE
created_at TIMESTAMP DEFAULT NOW()
```

#### 3. **broker_accounts** - Cuentas de broker
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
broker_type VARCHAR(50) NOT NULL  -- 'iqoption', 'olymptrade', etc.
email VARCHAR(255) NOT NULL
password_encrypted TEXT NOT NULL
is_demo BOOLEAN DEFAULT TRUE
balance DECIMAL(15,2)
is_connected BOOLEAN DEFAULT FALSE
last_sync TIMESTAMP
created_at TIMESTAMP DEFAULT NOW()
```

#### 4. **bots** - Bots de trading
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
name VARCHAR(255) NOT NULL
strategy VARCHAR(100) NOT NULL
symbol VARCHAR(20) NOT NULL
timeframe VARCHAR(10) DEFAULT 'M5'
is_active BOOLEAN DEFAULT FALSE
use_martingale BOOLEAN DEFAULT TRUE
max_gale_level INTEGER DEFAULT 2
initial_amount DECIMAL(10,2) DEFAULT 10.00
created_at TIMESTAMP DEFAULT NOW()
```

#### 5. **bot_stats** - Estadísticas de bots
```sql
id SERIAL PRIMARY KEY
bot_id INTEGER REFERENCES bots(id) ON DELETE CASCADE
total_trades INTEGER DEFAULT 0
winning_trades INTEGER DEFAULT 0
losing_trades INTEGER DEFAULT 0
profit_loss DECIMAL(15,2) DEFAULT 0.00
win_rate DECIMAL(5,2) DEFAULT 0.00
last_updated TIMESTAMP DEFAULT NOW()
```
    
#### 6. **trades** - Trades ejecutados
```sql
id SERIAL PRIMARY KEY
bot_id INTEGER REFERENCES bots(id) ON DELETE CASCADE
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
symbol VARCHAR(20) NOT NULL
direction VARCHAR(10) NOT NULL  -- 'CALL', 'PUT'
amount DECIMAL(10,2) NOT NULL
entry_price DECIMAL(15,5)
exit_price DECIMAL(15,5)
profit_loss DECIMAL(15,2)
is_win BOOLEAN
gale_level INTEGER DEFAULT 0
opened_at TIMESTAMP
closed_at TIMESTAMP
created_at TIMESTAMP DEFAULT NOW()
```

#### 7. **subscriptions** - Suscripciones
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
plan_type VARCHAR(50) NOT NULL
start_date TIMESTAMP NOT NULL
end_date TIMESTAMP NOT NULL
is_active BOOLEAN DEFAULT TRUE
payment_amount DECIMAL(10,2)
payment_method VARCHAR(50)
promo_code VARCHAR(50)
created_at TIMESTAMP DEFAULT NOW()
```

#### 8. **promo_codes** - Códigos promocionales
```sql
id SERIAL PRIMARY KEY
code VARCHAR(50) UNIQUE NOT NULL
type VARCHAR(20) NOT NULL  -- 'reseller', 'agent', 'courtesy'
duration_days INTEGER NOT NULL
max_uses INTEGER
current_uses INTEGER DEFAULT 0
is_active BOOLEAN DEFAULT TRUE
created_by INTEGER REFERENCES users(id)
created_at TIMESTAMP DEFAULT NOW()
expires_at TIMESTAMP
```

#### 9. **candles** - Datos de velas (Market Data)
```sql
id SERIAL PRIMARY KEY
symbol VARCHAR(20) NOT NULL
timeframe VARCHAR(10) NOT NULL
open DECIMAL(15,5) NOT NULL
high DECIMAL(15,5) NOT NULL
low DECIMAL(15,5) NOT NULL
close DECIMAL(15,5) NOT NULL
volume BIGINT
timestamp TIMESTAMP NOT NULL
created_at TIMESTAMP DEFAULT NOW()

UNIQUE(symbol, timeframe, timestamp)
INDEX idx_candles_symbol_time ON candles(symbol, timestamp)
```

#### 10. **payments** - Pagos
```sql
id SERIAL PRIMARY KEY
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
subscription_id INTEGER REFERENCES subscriptions(id)
amount DECIMAL(10,2) NOT NULL
payment_method VARCHAR(50)
status VARCHAR(20) DEFAULT 'pending'
transaction_id VARCHAR(255)
created_at TIMESTAMP DEFAULT NOW()
```

---

## 🔌 INTEGRACIONES EXTERNAS

### 1. IQ Option API
**Uso**: Trading en tiempo real
**Archivos**: `iq_client.py`, `iq_routes_redis_patch.py`
**Funciones**:
- Conexión a cuenta demo/real
- Ejecución de trades (CALL/PUT)
- Obtención de balance
- Datos de mercado OTC

### 2. Twelve Data API
**Uso**: Market data forex
**Variable**: `TWELVEDATA_API_KEY`
**Endpoint**: Real-time M1 candles EUR/USD, EUR/JPY

### 3. YFinance
**Uso**: Datos históricos
**Funciones**: Backfill de velas históricas

### 4. Finnhub API
**Uso**: Market data adicional
**Variable**: `FINNHUB_API_KEY`

### 5. Gmail SMTP
**Uso**: Sistema de emails
**Variables**:
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`

**Emails enviados**:
- Verificación de cuenta
- Recuperación de contraseña
- Notificaciones de suscripción
- Validación de broker
- Facturas de pago

---

## ⚙️ VARIABLES DE ENTORNO (Secrets)

```bash
# Base de Datos
DATABASE_URL=postgresql://user:password@host:port/database
PGHOST=hostname
PGPORT=5432
PGUSER=username
PGPASSWORD=password
PGDATABASE=database_name

# IQ Option
IQ_EMAIL=tu_email@ejemplo.com
IQ_PASSWORD=tu_password
IQ_BALANCE_TYPE=PRACTICE  # o REAL

# Market Data APIs
TWELVEDATA_API_KEY=tu_api_key
FINNHUB_API_KEY=tu_api_key

# Email System (Gmail SMTP)
GMAIL_USER=tu_email@gmail.com
GMAIL_APP_PASSWORD=tu_app_password

# Telegram Bot (opcional)
BOT_API_KEY=tu_bot_token

# Producción
REPLIT_DEPLOYMENT=1  # Indica si está en producción
```

---

## 📊 FLUJO DE TRADING AUTOMATIZADO

### 1. **Inicialización del Bot**
```python
# auto_trading_bot.py
bot = BotManager(bot_config)
bot.start()
```

### 2. **Análisis de Velas M5**
```python
# strategy_engine.py
signal = strategy_engine.analyze(candle_m5)
# Retorna: 'CALL', 'PUT', o None
```

### 3. **Ejecución de Trade**
```python
# iq_client.py
if signal == 'CALL':
    iq_client.buy(amount, 'call', duration_m5)
elif signal == 'PUT':
    iq_client.buy(amount, 'put', duration_m5)
```

### 4. **Gestión Martingala**
```python
# dual_gale_manager.py
if trade_result == 'loss':
    next_amount = dual_gale.calculate_next_gale(direction)
    # Ejecuta Gale 1 o Gale 2 según configuración
```

### 5. **Almacenamiento de Resultados**
```python
# database.py
trade = Trade(
    bot_id=bot_id,
    symbol=symbol,
    direction=direction,
    profit_loss=profit,
    is_win=(result == 'win')
)
db.add(trade)
db.commit()
```

---

## 🎨 SISTEMA PWA (Progressive Web App)

### Service Worker v3-admin-crud
**Archivo**: `static/sw.js`
**Versión**: `stc-ar-v3-admin-crud`

**Características**:
- **Estrategia**: Network First con fallback a Cache
- **Auto-Update**: Verificación cada 60 segundos
- **Recarga Automática**: Al detectar nueva versión
- **URLs Cacheadas**:
  - `/` - Landing page
  - `/auth/login` - Login
  - `/trading-charts` - Pantalla Venezuela
  - `/admin/users` - Gestión usuarios
  - Bootstrap CSS
  - Lightweight Charts JS

**Manifest PWA**:
```json
{
  "name": "smarttradetecnologies-ar",
  "short_name": "STC-AR",
  "theme_color": "#000000",
  "background_color": "#000000",
  "display": "standalone",
  "icons": [
    { "src": "/static/icons/icon-192x192.png", "sizes": "192x192" },
    { "src": "/static/icons/icon-512x512.png", "sizes": "512x512" }
  ]
}
```

---

## 🔐 SISTEMA DE AUTENTICACIÓN

### Flujo de Registro
1. Usuario completa formulario `/auth/register`
2. Sistema crea usuario con `is_email_verified=FALSE`
3. Email de verificación enviado con token único
4. Usuario hace click en enlace → Token validado → `is_email_verified=TRUE`
5. Login permitido solo si email verificado

### Flujo de Login
1. POST `/auth/login` con email + password
2. Verificación: Email verificado + Password correcto
3. Sesión creada con `user_id` en Flask session
4. Redirección según rol (admin → dashboard admin, user → trading charts)

### Recuperación de Contraseña
1. POST `/forgot-password` con email
2. Token de 32 caracteres generado (expira en 1 hora)
3. Email enviado con enlace `/reset-password?token=XXX`
4. Usuario ingresa nueva contraseña
5. Token marcado como usado + Password actualizado

### Protección de Rutas
```python
@login_required  # Requiere login
@admin_required  # Requiere rol admin
@requires_active_access  # Requiere suscripción activa o código promo
```

---

## 📈 GRÁFICOS PROFESIONALES

### Lightweight Charts
**Archivo**: `static/js/stc-charts.js`
**Librería**: TradingView Lightweight Charts 4.1.1

**Características**:
- Gráficos de velas en tiempo real
- Multi-timeframe (M1, M5, M15)
- Señales visuales CALL/PUT
- Bandera Venezuela como marca de agua
- Diseño glassmorphism 3D
- Touch-friendly para móviles
- Sonidos tecnológicos al cambiar timeframe

**Datos**:
- Origen: Twelve Data API (M1 real-time)
- Construcción M5: Agregación de 5 velas M1
- Actualización: Cada 3 segundos vía WebSocket

---

## 🧪 SISTEMA DE BACKTESTING

**Puerto**: 5000 (servidor independiente)
**Archivos**:
- `backtest/backtest_server.py`
- `backtest/backtest_dashboard.html`
- `backtesting_engine.py`

**Funcionalidades**:
- Simulaciones Monte Carlo hasta 10,000 escenarios
- Estrategia Break-Even Martingale
- Win Rate configurable (70%, 75%, 80%, 85%, 90%)
- Análisis de resultados:
  - Capital final promedio
  - ROI %
  - Tasa de éxito
  - Tasa de quiebra
  - Gales promedio

**Resultados WR 80%**:
- Capital promedio: $4,266 (+22% ROI)
- 99.9% de éxito
- 0% de quiebra

---

## 🚀 INICIO DEL SISTEMA EN PRODUCCIÓN

### Script de Inicio
**Archivo**: `start_production.py`

**Proceso**:
1. Ejecuta `populate_production.py`:
   - Inicializa base de datos
   - Crea usuario admin (admin@stc.com / admin123)
   - Crea 8 bots por defecto
   - Puebla códigos promocionales
2. Inicia 2 servidores en paralelo:
   - Dashboard Server (Port 5000)
   - RealTime Server (Port 8000)

### Workflows Configurados
```yaml
1. Dashboard Principal:
   - Comando: python dashboard_server.py
   - Puerto: 5000
   - Output: webview

2. RealTime Server:
   - Comando: python start_realtime_server.py
   - Puerto: 8000
   - Output: console
```

---

## 📧 SISTEMA DE EMAILS

**Archivo**: `email_service.py`
**Clase**: `EmailService`

**Templates HTML**:
- Verificación de cuenta
- Recuperación de contraseña
- Notificaciones de suscripción
- Validación de broker

**Configuración**:
```python
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = os.getenv('GMAIL_USER')
SMTP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
```

**Diseño**:
- Glassmorphism profesional
- Colores corporativos (cyan/negro)
- Responsive para móviles
- Logo y branding

---

## 🛡️ SEGURIDAD

### Passwords
- Hashing: `werkzeug.security` con `pbkdf2:sha256`
- Nunca almacenados en texto plano
- Validación de complejidad en frontend

### Tokens
- Verificación email: 32 caracteres hex
- Recuperación password: 32 caracteres hex + expiración 1 hora
- Un solo uso (marcado como `used=TRUE`)

### Sesiones
- Flask sessions con cookie segura
- Secret key único por entorno
- Expiración automática

### SQL Injection
- SQLAlchemy ORM protege automáticamente
- Prepared statements
- Input validation

### XSS Protection
- Templates HTML escapados automáticamente
- Content Security Policy headers
- Sanitización de inputs

---

## 📱 OPTIMIZACIÓN MÓVIL

### PWA Features
- Instalable como app nativa
- Funciona offline
- Service Worker con caché inteligente
- Icons optimizados (8 tamaños)

### Responsive Design
```css
/* Tablet */
@media (max-width: 768px) { ... }

/* Mobile */
@media (max-width: 480px) { ... }
```

### Touch Optimization
- Botones táctiles grandes (min 48x48px)
- Feedback visual al tocar
- Gestos swipe para navegación
- Zoom deshabilitado en inputs

---

## 🔄 FLUJO COMPLETO DE USUARIO

1. **Registro** → Email verificación → Login permitido
2. **Login** → Validación de acceso (suscripción o código promo)
3. **Pantalla Venezuela** → Código de acceso → Gráficos profesionales
4. **Trading Charts** → Selección de símbolo (EUR/USD, EUR/JPY)
5. **Gestión de Bots** → Activar/Desactivar bots
6. **Panel de Señales** → Ver señales en tiempo real multi-par
7. **Dashboard** → Monitoreo de rendimiento y estadísticas
8. **Admin Panel** (solo admins) → CRUD completo del sistema

---

## 📦 DEPENDENCIAS CRÍTICAS

Ver archivo `requirements.txt` completo.

**Más Críticas**:
- Flask 3.0.0 - Framework web
- SQLAlchemy 2.0.23 - ORM
- psycopg2-binary 2.9.9 - PostgreSQL driver
- FastAPI 0.104.1 - Real-time server
- iqoptionapi - Trading API
- pandas 2.1.3 - Data processing
- websockets 12.0 - Real-time communication

---

## 🔧 TROUBLESHOOTING

### Problema: Caché del navegador muestra versión antigua
**Solución**: Hard Refresh (Ctrl+Shift+R) o incrementar versión del Service Worker

### Problema: Email no llega
**Solución**: Verificar GMAIL_APP_PASSWORD y que el email no esté en spam

### Problema: Bot no ejecuta trades
**Solución**: Verificar:
1. Bot está activo (`is_active=TRUE`)
2. Usuario tiene suscripción o código promo válido
3. Cuenta IQ Option conectada
4. Suficiente balance

### Problema: WebSocket desconecta
**Solución**: Polling optimizado a 3s, verificar timeout configurado

### Problema: Base de datos lenta
**Solución**: Verificar índices en tabla `candles`:
```sql
CREATE INDEX idx_candles_symbol_time ON candles(symbol, timestamp);
```

---

## 📊 MÉTRICAS Y MONITOREO

### Logs del Sistema
- Dashboard Server: Console logs con timestamps
- RealTime Server: Uvicorn access logs
- Errores: Python logging con nivel INFO

### Métricas Clave
- Total usuarios registrados
- Usuarios activos (suscripciones vigentes)
- Total bots activos
- Total trades ejecutados
- Win rate promedio
- Profit/Loss total

### Alertas
- Email cuando suscripción expira
- Notificación cuando bot pierde 3 trades seguidos
- Alerta cuando balance < $10

---

## 🎯 ROADMAP Y MEJORAS FUTURAS

1. ✅ Sistema de recuperación de contraseña (COMPLETADO)
2. ✅ CRUD completo de usuarios en admin panel (COMPLETADO)
3. ✅ PWA con auto-update (COMPLETADO)
4. 🔄 Integración con más brokers (Quotex, Pocket Option)
5. 🔄 Dashboard móvil nativo (React Native)
6. 🔄 Sistema de afiliados y comisiones
7. 🔄 Trading social (copy trading entre usuarios)
8. 🔄 IA para optimización de estrategias

---

## 📝 NOTAS IMPORTANTES PARA BACKUP

### Archivos que NO deben incluirse en backup:
- `__pycache__/` - Cache de Python
- `.pythonlibs/` - Librerías instaladas
- `node_modules/` - Dependencias Node (si existen)
- `attached_assets/` - Screenshots temporales
- `.git/` - Si existe, opcional
- `*.pyc` - Archivos compilados Python

### Archivos CRÍTICOS que SÍ deben incluirse:
- ✅ Todos los `.py` del directorio raíz
- ✅ Carpeta `templates/` completa
- ✅ Carpeta `static/` completa
- ✅ Carpeta `realtime_trading/`
- ✅ Carpeta `backtest/`
- ✅ Carpeta `services/`
- ✅ `requirements.txt`
- ✅ `replit.md`
- ✅ Todos los archivos `.md` de documentación
- ✅ Archivos de configuración (`.replit`, `replit.nix`, `pyproject.toml`)

### Base de Datos:
**IMPORTANTE**: Hacer dump de PostgreSQL antes del backup:
```bash
pg_dump $DATABASE_URL > backup_database.sql
```

---

**Última Actualización**: 24 de Octubre, 2025
**Versión del Sistema**: v3-admin-crud
**Autor**: smarttradetecnologies-ar Team
**Producción**: https://Smart-Trade-Academy-IA.replit.app
