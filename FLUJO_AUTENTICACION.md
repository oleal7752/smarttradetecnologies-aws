# 🔐 FLUJO DE AUTENTICACIÓN Y ACCESO - SMARTTRADE ACADEMY 🇻🇪

## 📋 FLUJO COMPLETO DE USUARIO

### 1️⃣ **REGISTRO** (`/auth/login` → "Regístrate aquí")
```
Usuario ingresa:
- Email
- Contraseña
- Nombre y Apellido
- DNI
- Fecha de Nacimiento (debe ser mayor de 18 años)
- Teléfono
- País
- Tipo de Broker (IQ Option / Olymp Trade)
- ID de Cuenta de Broker
```

**Resultado:** Se crea usuario con `email_verified = False` y se envía email de verificación.

---

### 2️⃣ **VERIFICACIÓN DE EMAIL**
```
Usuario recibe email con enlace:
/api/auth/verify-email/<token>
```

**Resultado:** Usuario verificado (`email_verified = True`) y puede iniciar sesión.

---

### 3️⃣ **LOGIN** (`/auth/login`)
```
Usuario ingresa:
- Email
- Contraseña
```

**Validaciones:**
- ✅ Credenciales correctas
- ✅ Cuenta activa (`is_active = True`)
- ✅ Email verificado (`email_verified = True`)

**Resultado:** 
- Sesión creada
- Redirección automática:
  - **Admin** → `/admin`
  - **Usuario normal** → `/access-validation`

---

### 4️⃣ **VALIDACIÓN DE ACCESO** (`/access-validation`)

**Pantalla protegida con `@login_required`**

Usuario tiene 2 opciones:

#### Opción A: Ingresar Código Promocional
```
Ingresa código en el input
Sistema valida:
- Código existe
- Está activo (is_active = True)
- No está usado (is_used = False)
- No ha expirado (expires_at > now)
```

**Si es válido:**
- Asigna código al usuario (`assigned_to = user_id`)
- Marca como usado (`is_used = True`)
- Establece fecha de activación (`activated_at = now`)
- **Redirección automática** → `/welcome`

#### Opción B: Comprar Suscripción
```
Selecciona plan (Mensual/Trimestral/Anual)
Simula pago (en modo demo)
```

**Resultado:**
- Crea suscripción activa
- **Redirección automática** → `/welcome`

---

### 5️⃣ **PANTALLA DE BIENVENIDA** (`/welcome`)

**Protegida con `@login_required` + `@requires_active_access`**

Muestra:
- 🚀 Bienvenida personalizada
- ✅ Tipo de acceso (Suscripción o Código Promocional)
- 📅 Días restantes
- 📊 Features disponibles

**3 Botones de navegación:**

1. **🎯 PANEL DE SEÑALES** → `/signals`
   - Señales automáticas multi-par
   - Copy trading manual

2. **🇻🇪 GRÁFICOS PROFESIONALES** → `/trading-charts`
   - Pantalla con Bandera de Venezuela
   - Botón glassmorphism de acceso

3. **📊 DASHBOARD DE TRADING** → `/select-broker`
   - Selección de broker
   - Trading automatizado

---

### 6️⃣ **PANTALLA VENEZUELA** (`/trading-charts`)

**Protegida con `@login_required` + `@requires_active_access`**

Características:
- 🇻🇪 **Bandera de Venezuela** grande y centrada (300x200px)
- ✨ **Diseño Glassmorphism** negro espacial
- 🔊 **Sonido tipo iPhone** al hacer clic
- 📱 **Responsive** para móviles

**Botón:**
```
🚀 ACCEDER A LA ZONA DE OPERACIONES
```

**Al hacer clic:**
- Reproduce sonido tipo iPhone (1400Hz, 30ms)
- Redirige a → `/charts`

---

### 7️⃣ **GRÁFICOS PROFESIONALES** (`/charts` → `/static/demo/candlestick.html`)

**Protegida con `@login_required` + `@requires_active_access`**

Características:
- 📈 **Gráficos TradingView** con Lightweight Charts v4.1.1
- 🇻🇪 **Bandera Venezuela** en header izquierdo
- 🔊 **Sonidos tipo iPhone** en botones
- 💎 **Glassmorphism** extremo (rgba 0.01-0.05)
- ⏱️ **Reloj unificado** (FECHA + HORA + MS)

**Pares disponibles:**
- EUR/USD
- EUR/JPY

**Estrategias:**
- SmartTrade1 (Análisis de Probabilidades)
- SmartTrade2 (El Hacha - 3 Patrones)

**Marcadores:**
- 🔼 **CALL** (verde cyan)
- 🔽 **PUT** (rojo)

---

## 🔒 SISTEMA DE PROTECCIÓN DE RUTAS

### Decoradores Disponibles

#### 1. `@login_required`
```python
# Verifica que el usuario tenga sesión activa
# Si NO → Redirige a /auth/login
```

**Usado en:**
- `/welcome`
- `/access-validation`
- `/trading-charts`
- `/charts`
- `/signals`
- `/select-broker`
- `/dashboard/*`
- `/bots`
- `/monitor`

---

#### 2. `@requires_active_access`
```python
# Verifica que el usuario tenga:
# - Suscripción activa (status=ACTIVE, end_date > now) O
# - Código promocional válido (is_used=True, is_active=True, expires_at > now)
# Si NO → Redirige a /access-validation
```

**Usado en:**
- `/welcome`
- `/trading-charts`
- `/charts`
- `/signals`
- `/select-broker`
- `/dashboard/*`
- `/bots`

---

#### 3. `@admin_required`
```python
# Verifica que el usuario sea administrador (is_admin=True)
# Si NO → Error 403
```

**Usado en:**
- `/admin`
- `/admin/promo-codes`
- `/admin/broker-validation`

---

## 🎯 RUTAS PÚBLICAS (Sin protección)

```
/auth/login                    - Login
/api/auth/register             - Registro
/api/auth/verify-email/<token> - Verificación email
/api/market/*                  - Datos de mercado (Twelve Data)
/static/*                      - Archivos estáticos (pero /static/demo/candlestick.html redirige a /charts)
```

---

## 🎨 CARACTERÍSTICAS DE DISEÑO

### Glassmorphism Extremo
```css
background: rgba(0, 0, 0, 0.01);      /* Negro casi transparente */
border: 2px solid rgba(0, 255, 255, 0.25);  /* Cyan muy tenue */
backdrop-filter: blur(40px);           /* Desenfoque fuerte */
box-shadow: 0 0 100px rgba(0, 255, 255, 0.15);  /* Glow sutil */
```

### Símbolos de Venezuela
```
Header Izquierdo: 🇻🇪 Bandera (8 estrellas) - 50x33px desktop, 35x23px móvil
Marca de Agua: Bandera en centro del gráfico - opacity 3%
Border: rgba(255, 215, 0, 0.3) - Dorado sutil
```

### Sonidos tipo iPhone
```javascript
Frecuencia: 1300-1500 Hz
Duración: 30-40 ms
Tipo: Onda sinusoidal (sine)
Volumen: 0.12-0.15
```

---

## 📊 DATOS DE PRUEBA

### Usuario Admin (Pre-creado)
```
Email: admin@stc.com
Password: admin123
Acceso: TOTAL (sin necesidad de código/suscripción)
```

### Crear Código Promocional
```
1. Login como admin
2. Ir a /admin/promo-codes
3. Crear código:
   - Código: DEMO2024
   - Tipo: RESELLER
   - Duración: 30 días
   - Estado: Activo
```

---

## 🚀 FLUJO RÁPIDO DE PRUEBA

```bash
1. Abrir /auth/login
2. Login con admin@stc.com / admin123
3. Redirige a /welcome
4. Clic en "🇻🇪 GRÁFICOS PROFESIONALES"
5. Ver pantalla con Bandera de Venezuela
6. Clic en "🚀 ACCEDER A LA ZONA DE OPERACIONES"
7. Ver gráficos EUR/USD y EUR/JPY
```

---

## ✅ SEGURIDAD IMPLEMENTADA

✅ **Autenticación por sesión** (Flask session)
✅ **Verificación de email obligatoria**
✅ **Validación de edad** (mayor de 18 años)
✅ **Protección de rutas** con decoradores
✅ **Validación de códigos promocionales**
✅ **Expiración automática** de códigos y suscripciones
✅ **Redirecciones automáticas** según nivel de acceso
✅ **Sin archivos estáticos públicos** para gráficos
✅ **Todas las peticiones verificadas** en servidor

---

**🇻🇪 Sistema 100% protegido y funcional con identidad venezolana integrada**
