# 🔐 SISTEMA DE RECUPERACIÓN DE CONTRASEÑA

## ✅ IMPLEMENTACIÓN COMPLETA Y FUNCIONAL

La recuperación de contraseña es una funcionalidad **profesional y obligatoria** completamente implementada y funcional tanto en desarrollo como en producción.

---

## 🎯 FLUJO COMPLETO

### 1. Usuario Olvida Su Contraseña
- Va a la página de login
- Click en "¿Olvidaste tu contraseña?"
- Ingresa su email
- Click en "Enviar enlace de recuperación"

### 2. Sistema Envía Email
- Genera token único de 32 caracteres
- Token válido por **1 hora**
- Email profesional con diseño glassmorphism
- Link directo a página de reset

### 3. Usuario Hace Click en Email
- Abre email de Gmail
- Click en "RECUPERAR CONTRASEÑA"
- Redirigido a página de reset con token en URL

### 4. Usuario Crea Nueva Contraseña
- Ingresa nueva contraseña
- Confirma contraseña
- Click en "Restablecer Contraseña"

### 5. Sistema Valida y Actualiza
- Verifica token válido y no expirado
- Verifica token no usado
- Actualiza contraseña con hash seguro
- Marca token como usado
- Redirige automáticamente al login

---

## 📊 TABLAS DE BASE DE DATOS

### `password_resets`
```sql
CREATE TABLE password_resets (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_password_resets_user_id ON password_resets(user_id);
CREATE INDEX idx_password_resets_token ON password_resets(token);
CREATE INDEX idx_password_resets_expires_at ON password_resets(expires_at);
```

---

## 🔧 ARCHIVOS CLAVE

### Backend
- `auth_routes.py`: Rutas `/api/auth/request-password-reset` y `/api/auth/reset-password`
- `email_service.py`: Función `send_password_reset_email()`
- `database.py`: Modelo `PasswordReset`

### Frontend
- `templates/forgot_password.html`: Formulario para solicitar reset
- `templates/reset_password.html`: Formulario para nueva contraseña

---

## 🚀 INICIALIZACIÓN EN PRODUCCIÓN

El sistema se inicializa automáticamente cuando arranca:

```python
# init_admin.py (se ejecuta al inicio)
def create_admin_if_not_exists():
    print("🔧 Inicializando base de datos...")
    init_db()  # Crea TODAS las tablas incluyendo password_resets
    print("✅ Tablas creadas correctamente")
    # ... resto del código
```

**NO se requiere ninguna acción manual** para crear las tablas en producción.

---

## ✅ SEGURIDAD IMPLEMENTADA

1. **Tokens Únicos**: 32 caracteres aleatorios criptográficamente seguros
2. **Expiración**: 1 hora desde generación
3. **Un Solo Uso**: Token se marca como usado después del reset
4. **Hash de Contraseñas**: Werkzeug con salt automático
5. **No Revelación**: No informa si el email existe (por seguridad)
6. **Validación Doble**: Token debe ser válido Y no expirado Y no usado

---

## 📧 EMAIL PROFESIONAL

El email enviado incluye:
- **Asunto**: "Recupera tu contraseña - Smart Trade Academy"
- **Diseño**: Glassmorphism 3D con fondo negro
- **Contenido**: Instrucciones claras y enlace destacado
- **Expiración**: Indica que el link expira en 1 hora
- **Seguridad**: Advierte no compartir el link

---

## 🧪 TESTING

### Desarrollo
```
URL: https://[tu-dev-url].replit.dev/forgot-password
```

### Producción
```
URL: https://Smart-Trade-Academy-IA.replit.app/forgot-password
```

### Flujo de Prueba
1. Registra un usuario con email real
2. Ve a forgot-password
3. Ingresa el email
4. Revisa bandeja de entrada
5. Click en link del email
6. Ingresa nueva contraseña
7. Login con nueva contraseña ✅

---

## ⚙️ CONFIGURACIÓN

### Variables de Entorno Requeridas
```
GMAIL_USER=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password-de-gmail
DATABASE_URL=postgresql://...
```

### URLs Automáticas
- Desarrollo: Usa `REPLIT_DEV_DOMAIN`
- Producción: Usa URL fija de producción

---

## 🎯 ESTADO ACTUAL

✅ Tabla `password_resets` creada automáticamente
✅ Modelo `PasswordReset` definido en `database.py`
✅ Rutas API implementadas y funcionales
✅ Templates HTML con diseño glassmorphism
✅ Servicio de email configurado con Gmail SMTP
✅ Tokens seguros con expiración de 1 hora
✅ Validaciones completas de seguridad
✅ Inicialización automática en producción

**SISTEMA 100% FUNCIONAL Y LISTO PARA PRODUCCIÓN** ✅

---

## 📝 NOTAS IMPORTANTES

- Los tokens expiran en **1 hora** por seguridad
- Cada token solo puede usarse **una vez**
- Los emails se envían desde **Gmail SMTP profesional**
- La función está **habilitada** en desarrollo y producción
- **No requiere configuración manual** en producción

---

## 🆘 TROUBLESHOOTING

### "Token inválido"
- El token ya fue usado
- El token expiró (> 1 hora)
- El link está corrupto

**Solución**: Solicitar nuevo link de recuperación

### "Email no llegó"
- Revisar carpeta de spam
- Verificar que GMAIL_USER y GMAIL_APP_PASSWORD estén configurados
- Verificar que el email esté registrado en el sistema

**Solución**: Esperar 1-2 minutos o solicitar reenvío

---

## 🔄 ACTUALIZACIÓN Oct 24, 2025

- Implementación completa de recuperación de contraseña
- Inicialización automática de tablas en producción
- Sistema profesional y seguro
- Detección automática de ambiente (desarrollo/producción)
- URLs correctas según ambiente

**Autor**: Sistema STC Trading
**Última Actualización**: 24 de Octubre, 2025
