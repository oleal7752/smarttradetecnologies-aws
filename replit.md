# smarttradetecnologies-ar - Trading System

## Overview
smarttradetecnologies-ar es un sistema SaaS diseñado para vender suscripciones de bots de trading, integrándose con IQ Option para trading automatizado en tiempo real. Proporciona un panel web para gestión avanzada de bots, implementa estrategias sofisticadas de Martingala dual y soporta multi-tenencia. La plataforma busca establecer un modelo de negocio rentable basado en suscripciones de trading automatizado, ofreciendo herramientas avanzadas, datos de mercado en tiempo real y gestión robusta de suscripciones.

## PWA (Progressive Web App) - NUEVO (Oct 2025)
Sistema convertido a PWA para optimización móvil profesional:
- **Instalable:** Funciona como app nativa en móviles y escritorio
- **Offline Ready:** Service Worker con caché inteligente (Network First)
- **Iconos:** 8 tamaños (72px hasta 512px) con diseño cyber de velas
- **Manifest:** `/static/manifest.json` con tema negro (#000000) y cyan (#00ffff)
- **Service Worker:** `/static/sw.js` con estrategia de red primero
- **Optimización Móvil:** Media queries responsive para tablets (768px) y móviles (480px)
- **Touch-Friendly:** Botones táctiles optimizados con feedback visual
- **Auto-Update:** Refresco automático cuando hay nueva versión
- **Instalación:** Chrome/Edge ofrecen instalar automáticamente
- **Sonidos Tecnológicos:** Web Audio API generando sonidos tipo iPhone al tocar botones (clicks suaves 1300-1500Hz, duración 30-40ms)
- **Símbolos Venezuela:** Bandera (8 estrellas) en header izquierdo, marca de agua 3% opacity en gráfico
- **Multi-Timeframe:** 3 botones glassmorphism (M1, M5, M15) con sonidos y carga dinámica de velas según temporalidad seleccionada
- **Loader Moderno:** Spinner glassmorphism con texto "CARGANDO DATOS..." que aparece al cambiar pares o timeframes (Oct 2025)

## Backtest System (NEW - Oct 2025)
Sistema completo de backtesting con interfaz web para estrategia Break-Even Martingale:
- **Puerto:** 5000 (http://localhost:5000)
- **Velas:** 500 M5 simuladas EUR/USD
- **Simulaciones:** Hasta 10,000 escenarios Monte Carlo
- **Resultados WR 80%:** Capital promedio $4,266 (+22% ROI), 99.9% éxito, 0% quiebra
- **Archivos:** `/backtest/` (servidor Flask + dashboard glassmorphism 3D)
- **Ver:** `backtest/INSTRUCCIONES.md` para uso completo

## User Preferences
- **Preferred Language**: Spanish
- **Account Type**: IQ Option Practice Account (demo)
- **Business Model**: SaaS subscription-based platform con plan único de acceso completo (señales + bots + auto-ejecución), solo varía duración
- **Branding**: Nombre "smarttradetecnologies-ar" con eslogan "💰 Tecnología que multiplica capital" (Oct 2025)
- **Design Style**: Glassmorphism 3D espacial robótico con fondo negro absoluto, transparencias extremas (0.01-0.15), efectos 3D translateZ(), fuente monospace, blur 30-40px, sin degradaciones complejas, sin efectos glow
- **Flujo de Acceso**: Registro → Validación Email → Login → Pantalla Venezuela (`/trading-charts` con bandera clickeable + validación de código) → Gráficos Profesionales (`/charts`)
- **Símbolos Nacionales**: Bandera de Venezuela (8 estrellas, 650x433px) clickeable en pantalla de acceso, borde dorado, sin efectos glass

## System Architecture

### Core Architecture
The system employs a microservices-inspired architecture with dedicated services for candle data, trading symbols, broker account management, bot execution, and service orchestration.

### Production Configuration (Updated: Oct 24, 2025)
- **Deployment Type**: VM (always-on)
- **Startup Process**: `populate_production.py` → `start_production.py` (OPTIMIZADO)
- **Services Architecture OPTIMIZADA** (2 servidores en lugar de 3):
  - Dashboard Server (Port 5000): Main web interface + Backend API integrado
  - RealTime Server (Port 8000): FastAPI WebSocket server con polling cada 3s (optimizado)
- **Optimizaciones Anti-Guindar**:
  - Polling reducido de 1s a 3s (reduce CPU 66%)
  - Solo 2 procesos en lugar de 3 (reduce memoria 33%)
  - WebSocket con timeouts configurados
- **Service URLs**: Configurable via environment variables (BACKEND_API_URL, REALTIME_API_URL, REALTIME_WS_URL) with localhost defaults for internal communication
- **Auto-initialization**: Admin user (admin@stc.com / admin123) and 8 default bots created automatically on deployment
- **PWA Completo**: Sistema instalable como app nativa en móviles y escritorio

### UI/UX Decisions
The UI features a glassmorphism 3D robotic design with an absolute black background, extreme transparencies, 3D depth using `translateZ()`, `backdrop-filter blur 30-40px`, neon cyan borders, and multiple shadow effects. The color palette is predominantly black, neon cyan, and neon blue. Monospace fonts are used for a technical aesthetic. All UI panels incorporate 3D effects with interactive hover states. Components include a real-time 3D candle chart, interactive timeframe selectors, a spatial symbol modal, and a professional monitoring dashboard.

### Technical Implementations & Feature Specifications
- **Automated Trading Bots**: Supports 8 advanced strategies including RSI, MACD, Bollinger, and proprietary algorithms.
- **Dual Martingale System**: Manages independent CALL and PUT sequences.
- **Backtesting Engine**: Provides historical simulation capabilities with dynamic recalculation.
- **Real-time Data & Trade Execution**: Integrates with the IQ Option API.
- **Subscription Management**: Supports various tiers with simulated payment processing and automatic invoice generation.
- **Promotional Codes System**: Manages access to premium features via reseller, agent, and courtesy codes.
- **Access Control System**: Protects critical routes based on active subscriptions or valid promotional codes. New flow: Login → Access Validation → Welcome → Trading Charts (Venezuela screen) → Professional Charts (EUR/USD, EUR/JPY).
- **Visual Signals System**: Displays real-time visual trading signals on TradingView charts with multi-tenant security.
- **Admin Panel**: Comprehensive administration system for users, promo codes, bots, strategies, and pricing.
- **Multi-User Architecture**: Each user connects their own broker account, and bots operate independently.
- **System Design Choices**: Emphasizes modularity, a centralized strategy engine, integrated Martingale risk management, multi-tenancy, PostgreSQL scalability, and high availability. UTC is used consistently for all candle data.
- **Visual Trading Signals**: Integrates CALL/PUT signals into real-time charts with visual markers and confidence levels.
- **Multi-Pair Signals Panel (Copy Trading)**: A 3D glassmorphism dashboard for manual copy trading, displaying 4 simultaneous pairs. Bots initiate in an inactive state, generating immediate signals upon activation based on current M5 candle analysis.
- **Automatic Martingale System**: Automatically verifies results at M5 candle close and initiates Gale cycles upon losses.
- **Server Time Synchronization**: Ensures precise timing by using server-provided timestamps via WebSockets, eliminating reliance on client-side clocks.

### Database Schema
PostgreSQL is used with tables for `users`, `broker_accounts`, `subscriptions`, `payments`, `bots`, `bot_stats`, `trades`, `candles`, `promo_codes`, and backtesting data, optimized with key indexes.

### API Endpoints
Provides V1 & V2 APIs for candles, symbols, user balance, account management, and trade execution. Includes authentication endpoints (register, verify, login, logout, check-access), promotional code management, bot signals, access validation, and secure admin endpoints for system control and backtesting.

## External Dependencies
- **IQ Option API**: Real-time market data, account balance, and trade execution.
- **Twelve Data API**: Real forex market data.
- **YFinance**: Historical market data population.
- **PostgreSQL**: Primary database.
- **Flask**: Python web framework.
- **WebSockets**: Real-time communication.
- **MemoryRedis**: In-memory caching.
- **Chart.js**: JavaScript library for rendering charts.
- **SQLAlchemy**: ORM for database interactions.
- **Werkzeug**: Password hashing and security.
- **Python 3.11**: Core programming language.

## Email System (Producción) - ACTUALIZADO Oct 24, 2025
- **Sistema Profesional Activado**: Gmail SMTP con verificación obligatoria de email
- **Credenciales**: GMAIL_USER + GMAIL_APP_PASSWORD configurados en secrets
- **Emails Automáticos**:
  - ✅ Verificación de cuenta (registro)
  - ✅ Recuperación de contraseña
  - ✅ Notificaciones de suscripción
  - ✅ Validación de broker
  - ✅ Facturas de pago
- **Flujo Profesional**: Registro → Email verificación → Click enlace → Email verificado → Login permitido
- **Seguridad**: Login bloqueado para usuarios no verificados (transparencia y confianza)
- **Backup Manual**: `verify_user_production.py email@usuario.com` si hay problemas con Gmail SMTP

## Password Recovery System (Oct 24, 2025)
Sistema profesional de recuperación de contraseña vía email:
- **Rutas**: `/forgot-password` (solicitar), `/reset-password` (confirmar)
- **Tokens Seguros**: 32 caracteres aleatorios, expiración 1 hora, un solo uso
- **Tabla BD**: `password_resets` creada automáticamente en `init_admin.py`
- **Email HTML**: Diseño glassmorphism profesional con Gmail SMTP
- **Validaciones**: Token válido, no expirado, no usado, hash seguro de contraseñas
- **Testing**: Script `test_password_recovery.py` con 100% de pruebas exitosas
- **Documentación**: Ver `RECUPERACION_CONTRASENA.md` para flujo completo

## Admin Panel - CRUD Completo de Usuarios (Oct 24, 2025)
Panel de administración con gestión completa de usuarios:
- **CRUD Completo**: Create (via registro), Read, Update, Delete
- **Interfaz**: Tabla glassmorphism 3D con 4 botones de acción por usuario
- **Botones**:
  - ✏️ **EDITAR**: Modal glassmorphism para editar Email, Nombre, Apellido, DNI, Teléfono, País
  - **DESACTIVAR/ACTIVAR**: Toggle estado del usuario
  - **HACER ADMIN/QUITAR ADMIN**: Toggle permisos de administrador
  - 🗑️ **ELIMINAR**: Con doble confirmación de seguridad
- **Validaciones**: Email único, DNI único en edición
- **Seguridad**: 
  - Prevención de auto-eliminación del admin
  - Doble confirmación para eliminar usuarios
  - Eliminación en cascada de datos relacionados (bots, suscripciones, etc.)
- **Documentación**: Ver `ADMIN_CRUD_PRODUCCION.md` para troubleshooting de caché

## PWA Updates - Auto-Update System (Oct 24, 2025)
Sistema mejorado de actualización automática del Service Worker:
- **Versión**: `stc-ar-v3-admin-crud` (incrementada desde v2)
- **Auto-Update**: Verificación de nuevas versiones cada 60 segundos
- **Recarga Automática**: Cuando se detecta nueva versión del Service Worker
- **Caché URLs**: Incluye `/admin/users` y rutas principales del sistema
- **Prevención de Caché**: Hard refresh automático al actualizar producción

## Documentación Completa para Backup AWS (Oct 25, 2025)
Sistema completo de documentación técnica para backup y migración:
- **SISTEMA_COMPLETO.md**: Arquitectura técnica detallada del sistema completo
  - Stack tecnológico (Frontend, Backend, APIs, Infraestructura)
  - Estructura de directorios con todos los archivos
  - Base de datos PostgreSQL (10 tablas con esquemas completos)
  - Integraciones externas (IQ Option, Twelve Data, Gmail SMTP)
  - Variables de entorno requeridas
  - Flujo de trading automatizado paso a paso
  - Sistema PWA, autenticación, gráficos profesionales
  - Sistema de backtesting y troubleshooting
- **ARCHIVOS_CRITICOS.txt**: Lista completa de archivos esenciales para backup
  - ~91 archivos organizados por categoría
  - Servidores principales, autenticación, trading, templates, static
  - Archivos que NO deben incluirse (cache, librerías)
  - Variables de entorno requeridas en AWS
  - Instrucciones de backup de base de datos
- **BACKUP_AWS.md**: Guía paso a paso para migración a AWS
  - Pre-requisitos y herramientas necesarias
  - 3 opciones de backup de archivos (manual, git, script)
  - Scripts automatizados de backup completo
  - Configuración de EC2 (t3.medium) y RDS (PostgreSQL)
  - Migración completa del sistema a AWS
  - Configuración de variables de entorno
  - Servicios systemd para producción
  - Nginx como proxy reverso
  - Verificación post-migración completa
  - Troubleshooting y automatización de backups diarios
- **requirements.txt**: Dependencias Python 3.11 completas