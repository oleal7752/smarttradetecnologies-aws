# 🏗️ Arquitectura Multi-Usuario STC Trading System

## 📋 Resumen

Sistema SaaS multi-tenant para venta de suscripciones de bots de trading con soporte para múltiples brokers (IQ Option, MT5, OlympTrade).

## 🎯 Características Principales

### ✅ **Multi-Tenancy Completo**
- Cada usuario conecta **SU PROPIA cuenta** de broker
- Operaciones independientes por usuario
- Historial separado en BD con `user_id`

### ✅ **Alta Disponibilidad**
- Velas almacenadas en PostgreSQL
- Worker automático actualiza velas cada 5 segundos
- Cache compartido para optimización

### ✅ **Operación Manual y Automática**
- **Manual**: Usuario hace click CALL/PUT → Su cuenta
- **Automático**: Bot ejecuta trades → Cuenta del usuario
- Todo registrado en BD con `bot_id` (null=manual, id=auto)

## 🏛️ Arquitectura de Servicios

```
┌─────────────────────────────────────┐
│  USUARIO (user_id=123)              │
│  ├─ Suscripción activa              │
│  ├─ Broker: IQ Option               │
│  └─ Bots: [Bot RSI, Bot MACD]       │
└─────────────────┬───────────────────┘
                  │
    ┌─────────────▼─────────────┐
    │   COMPARTIDO (Todos)      │
    │                           │
    │  📊 Candle Service        │
    │     └─ BD PostgreSQL      │
    │        (alta disponib.)   │
    │                           │
    │  📈 Symbols Service       │
    │     └─ Cache global       │
    └───────────────────────────┘
                  │
    ┌─────────────▼─────────────────┐
    │   POR USUARIO (Individual)    │
    │                               │
    │  🔐 Account Manager           │
    │     └─ Conexión IQ por user   │
    │                               │
    │  🤖 Bot Executor              │
    │     └─ Bots del usuario       │
    └───────────────────────────────┘
                  │
    ┌─────────────▼─────────────────┐
    │   BASE DE DATOS               │
    │                               │
    │  • candles (histórico)        │
    │  • users                      │
    │  • broker_accounts            │
    │  • bots (user_id)             │
    │  • trades (user_id, bot_id)   │
    └───────────────────────────────┘
```

## 📁 Estructura de Archivos

### **Servicios** (`services/`)

#### 1. **candle_service.py** 🕯️
- Guarda velas en BD constantemente
- Sirve velas desde BD (alta disponibilidad)
- Histórico completo de velas
- Batch insert optimizado

#### 2. **symbols_service.py** 📊
- Cache global de pares disponibles
- Actualización cada 5 minutos
- Fallback predefinido si API falla

#### 3. **account_manager.py** 👤
- Gestión de cuentas por usuario
- Conexión individual a broker
- Soporta: IQ Option, MT5, OlympTrade
- Connection pooling automático

#### 4. **bot_executor.py** 🤖
- Ejecuta bots EN LA CUENTA del usuario
- Thread independiente por bot
- Guarda trades con `user_id` + `bot_id`

#### 5. **candle_worker.py** ⚙️
- Worker background
- Actualiza velas cada 5 segundos
- Guarda en BD automáticamente

#### 6. **service_manager.py** 🎛️
- Orquestador central
- Inicializa todos los servicios
- API unificada

## 🔄 Flujo de Operación

### **Operación Manual**
```python
# 1. Usuario hace login
session['user_id'] = 123

# 2. Conecta su cuenta
account = account_manager.get_account(123, 'iqoption')

# 3. Usuario click en CALL
result = account.place_order('EURUSD-OTC', 'CALL', 10)

# 4. Se guarda en BD
trades.insert({
    'user_id': 123,
    'bot_id': None,  # ← MANUAL
    'symbol': 'EURUSD-OTC',
    'direction': 'CALL',
    'result': result
})
```

### **Operación Automática (Bot)**
```python
# 1. Bot del usuario 123 detecta señal
bot_id = 5
user_id = 123

# 2. Bot ejecuta en cuenta del usuario
account = account_manager.get_account(123, 'iqoption')
result = account.place_order('EURUSD-OTC', 'PUT', 10)

# 3. Se guarda en BD
trades.insert({
    'user_id': 123,
    'bot_id': 5,  # ← AUTOMÁTICO
    'symbol': 'EURUSD-OTC',
    'direction': 'PUT',
    'result': result
})
```

## 📊 Esquema de Base de Datos

### **Tabla: candles** (Nueva)
```sql
CREATE TABLE candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 4) DEFAULT 0,
    broker VARCHAR(20) DEFAULT 'iqoption',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp, broker)
);
```

### **Tabla: trades** (Actualizada)
```sql
ALTER TABLE trades 
ADD COLUMN bot_id INTEGER REFERENCES bots(id);
```

- `bot_id = NULL` → Operación manual
- `bot_id = 5` → Operación automática (Bot RSI)

## 🚀 API Endpoints

### **V1 (Legacy - Compatibilidad)**
- `/api/iq/candles` - Velas desde cache memoria
- `/api/iq/symbols` - Símbolos desde API
- `/api/iq/trade` - Trade general

### **V2 (Multi-Usuario)**
- `/api/v2/candles` - Velas desde BD (alta disponib.)
- `/api/v2/symbols` - Símbolos desde cache compartido
- `/api/v2/user/account` - Conectar cuenta usuario
- `/api/v2/user/trade` - Trade en cuenta del usuario
- `/api/v2/user/disconnect` - Desconectar usuario

## 🔧 Uso

### **Inicializar Servicios**
```python
from services.service_manager import service_manager

# Inicializar
service_manager.initialize()

# Iniciar worker de velas
service_manager.start_candle_worker(iq_client)
```

### **Conectar Usuario**
```python
# Obtener cuenta del usuario
account = service_manager.get_user_account(user_id=123, broker='iqoption')

# Verificar conexión
if account and account.connected:
    balance = account.get_balance()
```

### **Ejecutar Trade**
```python
# Manual
result = account.place_order('EURUSD-OTC', 'CALL', 10)

# Automático (Bot)
bot_executor.start_bot(bot_id=5, user_id=123, strategy_engine, candle_service)
```

## 📈 Ventajas

### **Optimización**
- ✅ 1 request de velas sirve a 1000 usuarios
- ✅ Cache compartido reduce 90% requests
- ✅ Worker background mantiene BD actualizada

### **Escalabilidad**
- ✅ Cada usuario su conexión independiente
- ✅ Servicios separados y especializados
- ✅ Fácil agregar nuevos brokers (MT5, OlympTrade)

### **Alta Disponibilidad**
- ✅ Velas en BD siempre disponibles
- ✅ Fallback automático si API falla
- ✅ Histórico completo para backtesting

### **Multi-Broker (Preparado)**
- ✅ IQ Option: Implementado ✅
- ✅ MT5: Estructura lista
- ✅ OlympTrade: Estructura lista

## 🛠️ Próximos Pasos

1. Implementar MT5AccountManager
2. Implementar OlympTradeAccountManager
3. Dashboard con selector de broker
4. Panel de control de bots por usuario
5. Métricas y analytics por usuario

---

**Desarrollado por STC Trading - Smart Trade Academy** 🚀
