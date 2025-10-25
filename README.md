# STC Trading System - Smart Trade Academy

Sistema SaaS de señales de trading para opciones binarias con acceso controlado por códigos promocionales.

## 🚀 Características

- ✅ Sistema multi-tenant para trading automatizado
- ✅ Señales CALL/PUT en tiempo real (M5)
- ✅ Sistema Martingale automático
- ✅ Integración con IQ Option y Twelve Data API
- ✅ Dashboard glassmorphism 3D espacial
- ✅ Gestión de suscripciones y códigos promocionales
- ✅ 8 estrategias de trading avanzadas

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 15+
- Secrets requeridos (ver instalación)

## 🛠️ Instalación

### 1. Clonar repositorio
```bash
git clone https://github.com/TU_USUARIO/SmartTradeAcademy.git
cd SmartTradeAcademy
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crear archivo `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/stc_db
TWELVEDATA_API_KEY=tu_api_key
IQ_EMAIL=tu_email
IQ_PASSWORD=tu_password
IQ_BALANCE_TYPE=PRACTICE
GMAIL_USER=tu_gmail
GMAIL_APP_PASSWORD=tu_app_password
```

### 4. Inicializar base de datos
```bash
python populate_production.py
```

### 5. Ejecutar aplicación
```bash
python start_system.py
```

Acceder: `http://localhost:5000`

## 📦 Estructura del Proyecto

- `dashboard_server.py` - Servidor principal Flask
- `start_realtime_server.py` - Servidor WebSocket FastAPI
- `strategy_engine.py` - Motor de estrategias de trading
- `dual_gale_manager.py` - Sistema Martingale
- `templates/` - Templates HTML
- `static/` - Archivos estáticos (CSS, JS)

## 🔒 Seguridad

- Nunca subas el archivo `.env` al repositorio
- Usa variables de entorno para secrets
- Mantén actualizadas las dependencias

## 📄 Licencia

Propietario - Smart Trade Academy
