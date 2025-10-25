# 🎯 GUÍA DE ACCESO CON CÓDIGOS DE CORTESÍA

## 📋 Flujo Completo de Acceso

### 1️⃣ REGISTRO
- URL: `/auth/login`
- El usuario se registra con:
  - Email
  - Contraseña
  - Datos personales (nombre, apellido, DNI, etc.)
  - Datos de broker (IQ Option, Olymp Trade)

### 2️⃣ VALIDACIÓN DE EMAIL
- El sistema envía un email de verificación
- El usuario hace clic en el enlace del email
- Endpoint: `GET /api/auth/verify-email/<token>`

### 3️⃣ LOGIN
- URL: `/auth/login`
- El usuario ingresa email y contraseña
- Si las credenciales son correctas → Redirige a `/access-validation`

### 4️⃣ MÓDULO DE VALIDACIÓN DE ACCESO
- URL: `/access-validation`
- El usuario tiene 2 opciones:
  
  **Opción A: Comprar Suscripción**
  - Selecciona un plan (Mensual, Trimestral, Semestral, Anual)
  - Procesa el pago (simulado)
  - Obtiene acceso al sistema
  
  **Opción B: Ingresar Código Promocional** 🎁
  - Ingresa el código de cortesía
  - Endpoint: `POST /api/promo/activate`
  - Si el código es válido → Activa acceso

### 5️⃣ PANTALLA DE BIENVENIDA
- URL: `/welcome`
- Muestra información del usuario
- Muestra tipo de acceso (Suscripción o Código Promocional)
- Botones de acceso:
  - 🎯 **PANEL DE SEÑALES** → `/signals`
  - 📊 **DASHBOARD DE TRADING** → `/select-broker`

### 6️⃣ PANEL DE SEÑALES
- URL: `/signals` ⚠️ **PROTEGIDO**
- Requiere: Sesión activa + (Suscripción válida O Código promocional activo)
- Si no tiene acceso → Redirige a `/access-validation`

---

## 🔐 Sistema de Protección

### Decoradores de Acceso

```python
@login_required  # Requiere sesión activa
@requires_active_access  # Requiere suscripción O código promocional válido
```

### Validación Automática

El sistema valida automáticamente:
- ✅ Usuario autenticado (sesión activa)
- ✅ Suscripción activa (si existe)
- ✅ Código promocional válido y no expirado (si existe)

Si no cumple → Redirige a `/access-validation`

---

## 📊 Tipos de Códigos Promocionales

### 1. Código de Cortesía (`cortesia`)
- Duración personalizable (horas)
- Acceso temporal al sistema
- Se asigna a un usuario específico
- Un solo uso

### 2. Código de Revendedor (`revendedor`)
- Para distribuidores autorizados
- Múltiples usos posibles
- Duración configurable

### 3. Código de Agente (`agente`)
- Para agentes de ventas
- Acceso promocional
- Duración limitada

---

## 🔧 Endpoints Clave

### Autenticación
- `POST /api/auth/register` - Registro de usuario
- `GET /api/auth/verify-email/<token>` - Verificar email
- `POST /api/auth/login` - Inicio de sesión
- `POST /api/auth/logout` - Cerrar sesión
- `GET /api/auth/check-access` - Verificar acceso actual

### Códigos Promocionales
- `POST /api/promo/activate` - Activar código promocional
  ```json
  {
    "code": "TU_CODIGO_AQUI"
  }
  ```

### Suscripciones
- `POST /api/subscriptions/purchase` - Comprar suscripción
  ```json
  {
    "plan": "MONTHLY",
    "amount": 200
  }
  ```

---

## 🎨 Diseño Glassmorphism 3D

Todas las pantallas usan:
- Fondo negro absoluto (#000000)
- Transparencias extremas (0.02-0.15)
- Blur 40px en paneles
- Efectos 3D con `translateZ()`
- Colores neón cyan (#00ffff) y azul (#0099ff)
- Fuente monospace (Courier New)
- Bordes y sombras neón

---

## ✅ Estado Actual del Sistema

### Workflows RUNNING
- ✅ Dashboard - Puerto 5000
- ✅ RealTime Server - Puerto 8000

### Integraciones Activas
- ✅ Twelve Data API - Datos de mercado real
- ✅ PostgreSQL - Base de datos
- ✅ WebSocket - Comunicación en tiempo real

### Rutas Protegidas
- ✅ `/signals` - Panel de señales (requiere acceso)
- ✅ `/select-broker` - Selector de broker (requiere acceso)
- ✅ `/dashboard/*` - Dashboards de trading (requieren acceso)
- ✅ `/bot-manager` - Gestión de bots (requiere acceso)

---

## 🚀 Cómo Probar el Sistema

### 1. Crear Código de Cortesía (Admin)
1. Login como admin: `admin@stctrading.com / Admin123`
2. Ir a `/admin/promo-codes`
3. Crear código de cortesía
4. Copiar el código generado

### 2. Registrar Usuario
1. Ir a `/auth/login`
2. Clic en "Registrarse"
3. Completar formulario
4. Verificar email (revisar logs si es entorno demo)

### 3. Activar Código
1. Login con usuario registrado
2. Redirige automáticamente a `/access-validation`
3. Ingresar código de cortesía
4. Clic en "VALIDAR"

### 4. Acceder al Panel
1. Redirige a `/welcome`
2. Clic en "🎯 PANEL DE SEÑALES"
3. ¡Listo! Acceso al sistema de trading

---

## 🔍 Verificar Acceso

El usuario puede verificar su acceso en:
- Pantalla de bienvenida (`/welcome`)
- Endpoint: `GET /api/auth/check-access`

Respuesta con código válido:
```json
{
  "success": true,
  "has_access": true,
  "access_via": "promo_code",
  "user": {...},
  "promo_code": {
    "code": "CODIGO123",
    "expires_at": "2025-10-16T04:00:00"
  }
}
```

---

## ⚠️ Notas Importantes

1. **Códigos de un solo uso**: Una vez activado, el código queda marcado como `is_used=True`
2. **Expiración automática**: Los códigos expiran según `expires_at`
3. **Validación en tiempo real**: Cada request valida acceso actual
4. **Redirección automática**: Sin acceso → `/access-validation`
5. **Multi-tenant**: Cada usuario tiene su propio acceso independiente

---

## 📝 Credenciales Demo

**Admin:**
- Email: `admin@stctrading.com`
- Password: `Admin123`
- Acceso: Panel de administración + códigos promocionales

**Usuario de Prueba:**
- Crear nuevo usuario en `/auth/login`
- Usar código de cortesía generado por admin
