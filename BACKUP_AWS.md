# 🚀 GUÍA COMPLETA: BACKUP Y MIGRACIÓN A AWS

## 📋 ÍNDICE
1. [Pre-requisitos](#pre-requisitos)
2. [Backup de Archivos](#backup-de-archivos)
3. [Backup de Base de Datos](#backup-de-base-de-datos)
4. [Configuración en AWS](#configuración-en-aws)
5. [Migración del Sistema](#migración-del-sistema)
6. [Variables de Entorno](#variables-de-entorno)
7. [Verificación Post-Migración](#verificación-post-migración)
8. [Troubleshooting](#troubleshooting)

---

## 1️⃣ PRE-REQUISITOS

### Herramientas Necesarias
```bash
# En tu máquina local
- AWS CLI v2+
- Python 3.11
- PostgreSQL client (psql)
- Git (opcional)
- ZIP o TAR para comprimir archivos
```

### Cuenta AWS
- ✅ Cuenta AWS activa
- ✅ IAM user con permisos:
  - EC2 (launch instances)
  - RDS (create database)
  - S3 (storage)
  - CloudWatch (logs)
- ✅ Key pair (.pem) para SSH

---

## 2️⃣ BACKUP DE ARCHIVOS

### Opción A: Descarga Manual desde Replit

1. **Crear archivo comprimido en Replit**:
```bash
# En la consola de Replit
cd /home/runner/smarttradetecnologies-ar

# Excluir archivos innecesarios
tar -czf stc_backup_$(date +%Y%m%d).tar.gz \
  --exclude='__pycache__' \
  --exclude='.pythonlibs' \
  --exclude='node_modules' \
  --exclude='attached_assets' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='venv' \
  .
```

2. **Descargar el archivo**:
- Aparecerá `stc_backup_YYYYMMDD.tar.gz` en el explorador de archivos
- Click derecho → Download

### Opción B: Clonar desde Git (si tienes repo)

```bash
git clone https://github.com/tu-usuario/smarttradetecnologies-ar.git
cd smarttradetecnologies-ar
```

### Opción C: Usar Script Automatizado

```bash
# Crear script backup_to_aws.sh en Replit
#!/bin/bash

echo "🔧 Creando backup del sistema..."

# Fecha actual
FECHA=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_$FECHA"

# Crear directorio temporal
mkdir -p $BACKUP_DIR

# Copiar archivos críticos (ver ARCHIVOS_CRITICOS.txt)
echo "📂 Copiando archivos Python..."
cp *.py $BACKUP_DIR/

echo "📂 Copiando templates..."
cp -r templates $BACKUP_DIR/

echo "📂 Copiando static..."
cp -r static $BACKUP_DIR/

echo "📂 Copiando servicios..."
cp -r services $BACKUP_DIR/
cp -r realtime_trading $BACKUP_DIR/
cp -r backtest $BACKUP_DIR/

echo "📂 Copiando configuración..."
cp requirements.txt $BACKUP_DIR/
cp replit.nix $BACKUP_DIR/
cp .replit $BACKUP_DIR/
cp pyproject.toml $BACKUP_DIR/ 2>/dev/null || true

echo "📂 Copiando documentación..."
cp *.md $BACKUP_DIR/
cp *.txt $BACKUP_DIR/ 2>/dev/null || true

# Comprimir
echo "🗜️ Comprimiendo backup..."
tar -czf stc_backup_$FECHA.tar.gz $BACKUP_DIR

# Limpiar
rm -rf $BACKUP_DIR

echo "✅ Backup completado: stc_backup_$FECHA.tar.gz"
ls -lh stc_backup_$FECHA.tar.gz
```

---

## 3️⃣ BACKUP DE BASE DE DATOS

### Exportar PostgreSQL desde Replit

```bash
# En la consola de Replit
pg_dump $DATABASE_URL > backup_database_$(date +%Y%m%d).sql

# Verificar que se creó correctamente
ls -lh backup_database_*.sql

# Comprimir para ahorrar espacio
gzip backup_database_$(date +%Y%m%d).sql
```

### Exportar tablas específicas (opcional)

```bash
# Solo exportar estructura (sin datos)
pg_dump --schema-only $DATABASE_URL > schema_only.sql

# Solo exportar datos
pg_dump --data-only $DATABASE_URL > data_only.sql

# Exportar tabla específica
pg_dump -t users $DATABASE_URL > users_table.sql
```

### Script Completo de Backup BD

```bash
#!/bin/bash
# backup_database.sh

echo "🗄️ Iniciando backup de base de datos..."

FECHA=$(date +%Y%m%d_%H%M%S)

# Backup completo
echo "📊 Exportando base de datos completa..."
pg_dump $DATABASE_URL > backup_db_full_$FECHA.sql

# Backup de tablas críticas individualmente (por seguridad)
echo "📋 Exportando tablas críticas..."
pg_dump -t users $DATABASE_URL > backup_users_$FECHA.sql
pg_dump -t bots $DATABASE_URL > backup_bots_$FECHA.sql
pg_dump -t trades $DATABASE_URL > backup_trades_$FECHA.sql
pg_dump -t subscriptions $DATABASE_URL > backup_subscriptions_$FECHA.sql
pg_dump -t promo_codes $DATABASE_URL > backup_promo_codes_$FECHA.sql
pg_dump -t password_resets $DATABASE_URL > backup_password_resets_$FECHA.sql

# Comprimir todo
echo "🗜️ Comprimiendo backups..."
tar -czf backup_database_$FECHA.tar.gz backup_*_$FECHA.sql

# Limpiar archivos individuales
rm backup_*_$FECHA.sql

echo "✅ Backup de BD completado: backup_database_$FECHA.tar.gz"
ls -lh backup_database_$FECHA.tar.gz
```

---

## 4️⃣ CONFIGURACIÓN EN AWS

### Paso 1: Crear Instancia EC2

```bash
# Configuración recomendada
Instance Type: t3.medium (2 vCPU, 4 GiB RAM)
AMI: Ubuntu Server 22.04 LTS
Storage: 20 GB gp3
Security Group:
  - SSH (22) - Tu IP
  - HTTP (80) - 0.0.0.0/0
  - HTTPS (443) - 0.0.0.0/0
  - Custom TCP (5000) - 0.0.0.0/0 (Dashboard)
  - Custom TCP (8000) - 0.0.0.0/0 (RealTime)
```

### Paso 2: Crear Base de Datos RDS (PostgreSQL)

```bash
# Configuración RDS
Engine: PostgreSQL 15.x
Instance Class: db.t3.micro (para desarrollo) o db.t3.small (producción)
Storage: 20 GB gp3
DB Name: stc_trading
Master Username: stc_admin
Master Password: [generar password seguro]
Public Access: Yes (para migración, luego cambiar a No)
VPC Security Group: Permitir puerto 5432 desde EC2
```

### Paso 3: Conectarse a EC2

```bash
# Desde tu máquina local
chmod 400 tu-keypair.pem
ssh -i "tu-keypair.pem" ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com
```

---

## 5️⃣ MIGRACIÓN DEL SISTEMA

### Paso 1: Instalar Dependencias en EC2

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Instalar PostgreSQL client
sudo apt install -y postgresql-client

# Instalar Nginx (opcional, para proxy reverso)
sudo apt install -y nginx

# Instalar Git
sudo apt install -y git
```

### Paso 2: Subir Archivos a EC2

**Opción A: Usando SCP**
```bash
# Desde tu máquina local
scp -i "tu-keypair.pem" stc_backup_YYYYMMDD.tar.gz ubuntu@ec2-xx-xx-xx-xx:~/
scp -i "tu-keypair.pem" backup_database_YYYYMMDD.tar.gz ubuntu@ec2-xx-xx-xx-xx:~/
```

**Opción B: Usando S3 como intermediario**
```bash
# En tu máquina local
aws s3 cp stc_backup_YYYYMMDD.tar.gz s3://tu-bucket/backups/
aws s3 cp backup_database_YYYYMMDD.tar.gz s3://tu-bucket/backups/

# En EC2
aws s3 cp s3://tu-bucket/backups/stc_backup_YYYYMMDD.tar.gz ./
aws s3 cp s3://tu-bucket/backups/backup_database_YYYYMMDD.tar.gz ./
```

### Paso 3: Extraer y Configurar

```bash
# En EC2
cd /home/ubuntu

# Crear directorio del proyecto
mkdir -p /home/ubuntu/stc-trading
cd /home/ubuntu/stc-trading

# Extraer backup
tar -xzf ~/stc_backup_YYYYMMDD.tar.gz
mv backup_YYYYMMDD_HHMMSS/* .
rmdir backup_YYYYMMDD_HHMMSS

# Dar permisos
chmod +x *.py
```

### Paso 4: Crear Virtual Environment

```bash
# Crear venv
python3.11 -m venv venv

# Activar venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5: Restaurar Base de Datos

```bash
# Extraer backup de BD
tar -xzf ~/backup_database_YYYYMMDD.tar.gz

# Conectar a RDS y restaurar
export RDS_HOST="stc-db.xxxxxxxxx.us-east-1.rds.amazonaws.com"
export RDS_PORT="5432"
export RDS_DB="stc_trading"
export RDS_USER="stc_admin"
export RDS_PASSWORD="tu_password_seguro"

# Restaurar
psql -h $RDS_HOST -p $RDS_PORT -U $RDS_USER -d $RDS_DB < backup_db_full_YYYYMMDD.sql

# Verificar
psql -h $RDS_HOST -p $RDS_PORT -U $RDS_USER -d $RDS_DB -c "\dt"
```

---

## 6️⃣ VARIABLES DE ENTORNO

### Crear archivo .env

```bash
# En EC2: /home/ubuntu/stc-trading/.env
nano .env
```

```bash
# Base de Datos RDS
DATABASE_URL=postgresql://stc_admin:tu_password@stc-db.xxxxxxxxx.us-east-1.rds.amazonaws.com:5432/stc_trading
PGHOST=stc-db.xxxxxxxxx.us-east-1.rds.amazonaws.com
PGPORT=5432
PGUSER=stc_admin
PGPASSWORD=tu_password_seguro
PGDATABASE=stc_trading

# IQ Option
IQ_EMAIL=tu_email@ejemplo.com
IQ_PASSWORD=tu_password_iq
IQ_BALANCE_TYPE=PRACTICE

# Market Data APIs
TWELVEDATA_API_KEY=tu_api_key_twelve
FINNHUB_API_KEY=tu_api_key_finnhub

# Email System (Gmail SMTP)
GMAIL_USER=tu_email@gmail.com
GMAIL_APP_PASSWORD=tu_app_password_gmail

# Telegram (opcional)
BOT_API_KEY=tu_bot_token

# Producción
REPLIT_DEPLOYMENT=1
```

```bash
# Proteger archivo
chmod 600 .env
```

---

## 7️⃣ INICIAR EL SISTEMA

### Paso 1: Inicializar Admin

```bash
# Activar venv si no está activo
source venv/bin/activate

# Inicializar admin y base de datos
python init_admin.py
```

### Paso 2: Iniciar Servidores

**Opción A: Usando screen (recomendado para testing)**
```bash
# Terminal 1: Dashboard Server
screen -S dashboard
source venv/bin/activate
python dashboard_server.py

# Detach: Ctrl+A, D

# Terminal 2: RealTime Server
screen -S realtime
source venv/bin/activate
python start_realtime_server.py

# Detach: Ctrl+A, D

# Listar screens activos
screen -ls

# Re-attach a screen
screen -r dashboard
```

**Opción B: Usando systemd (producción)**

Crear servicio para Dashboard:
```bash
sudo nano /etc/systemd/system/stc-dashboard.service
```

```ini
[Unit]
Description=STC Dashboard Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stc-trading
Environment="PATH=/home/ubuntu/stc-trading/venv/bin"
ExecStart=/home/ubuntu/stc-trading/venv/bin/python dashboard_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Crear servicio para RealTime:
```bash
sudo nano /etc/systemd/system/stc-realtime.service
```

```ini
[Unit]
Description=STC RealTime Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stc-trading
Environment="PATH=/home/ubuntu/stc-trading/venv/bin"
ExecStart=/home/ubuntu/stc-trading/venv/bin/python start_realtime_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Habilitar e iniciar servicios:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stc-dashboard
sudo systemctl enable stc-realtime
sudo systemctl start stc-dashboard
sudo systemctl start stc-realtime

# Verificar estado
sudo systemctl status stc-dashboard
sudo systemctl status stc-realtime

# Ver logs
sudo journalctl -u stc-dashboard -f
sudo journalctl -u stc-realtime -f
```

### Paso 3: Configurar Nginx (Proxy Reverso)

```bash
sudo nano /etc/nginx/sites-available/stc-trading
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com;  # o IP pública de EC2

    # Dashboard Server
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # RealTime Server WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # RealTime Server API
    location /api/realtime/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/stc-trading /etc/nginx/sites-enabled/

# Verificar configuración
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

---

## 8️⃣ VERIFICACIÓN POST-MIGRACIÓN

### Checklist de Verificación

```bash
# 1. Servidores corriendo
sudo systemctl status stc-dashboard
sudo systemctl status stc-realtime

# 2. Base de datos conectada
python -c "from database import get_db; print('BD OK' if get_db() else 'BD ERROR')"

# 3. Verificar admin user existe
psql $DATABASE_URL -c "SELECT email, is_admin FROM users WHERE is_admin=TRUE;"

# 4. Test de endpoints
curl http://localhost:5000/
curl http://localhost:8000/api/status

# 5. WebSocket funcional
# Usar herramienta online: https://www.websocket.org/echo.html
# URL: ws://TU_IP_PUBLICA:8000/ws/live

# 6. Emails funcionales
python -c "from email_service import email_service; email_service.send_test_email('tu@email.com')"
```

### URLs de Acceso

```
Landing Page: http://TU_IP_PUBLICA/
Login: http://TU_IP_PUBLICA/auth/login
Admin Panel: http://TU_IP_PUBLICA/admin/users
Trading Charts: http://TU_IP_PUBLICA/trading-charts
WebSocket: ws://TU_IP_PUBLICA:8000/ws/live
```

---

## 9️⃣ TROUBLESHOOTING

### Problema: No se puede conectar a RDS
```bash
# Verificar Security Group permite conexiones desde EC2
# Verificar RDS está en "Available"
# Test de conexión
psql -h $RDS_HOST -p $RDS_PORT -U $RDS_USER -d $RDS_DB -c "\l"
```

### Problema: Módulos Python no encontrados
```bash
# Activar venv
source venv/bin/activate

# Re-instalar requirements
pip install -r requirements.txt --force-reinstall
```

### Problema: Puertos bloqueados
```bash
# Verificar puertos en uso
sudo netstat -tulpn | grep :5000
sudo netstat -tulpn | grep :8000

# Verificar Security Group de EC2 permite 5000 y 8000
```

### Problema: Service Worker caché vieja
```bash
# Incrementar versión en static/sw.js
# Línea 3: const CACHE_NAME = 'stc-ar-v4-aws';
```

### Problema: Emails no se envían
```bash
# Verificar variables de entorno
echo $GMAIL_USER
echo $GMAIL_APP_PASSWORD

# Test SMTP
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls(); print('SMTP OK')"
```

---

## 🔟 AUTOMATIZACIÓN DE BACKUPS

### Script de Backup Automático en AWS

```bash
# /home/ubuntu/scripts/backup_daily.sh
#!/bin/bash

FECHA=$(date +%Y%m%d)
BACKUP_DIR="/home/ubuntu/backups"
S3_BUCKET="s3://tu-bucket/backups"

mkdir -p $BACKUP_DIR

# Backup de archivos
cd /home/ubuntu/stc-trading
tar -czf $BACKUP_DIR/stc_files_$FECHA.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  .

# Backup de base de datos
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/stc_db_$FECHA.sql.gz

# Subir a S3
aws s3 cp $BACKUP_DIR/stc_files_$FECHA.tar.gz $S3_BUCKET/
aws s3 cp $BACKUP_DIR/stc_db_$FECHA.sql.gz $S3_BUCKET/

# Limpiar backups locales mayores a 7 días
find $BACKUP_DIR -name "stc_*" -mtime +7 -delete

echo "✅ Backup completado: $FECHA"
```

### Configurar Cron Job

```bash
# Editar crontab
crontab -e

# Agregar backup diario a las 3 AM
0 3 * * * /home/ubuntu/scripts/backup_daily.sh >> /home/ubuntu/logs/backup.log 2>&1
```

---

## 🎯 RESUMEN DE COMANDOS RÁPIDOS

```bash
# === BACKUP EN REPLIT ===
tar -czf stc_backup.tar.gz --exclude='__pycache__' .
pg_dump $DATABASE_URL > backup_db.sql

# === MIGRACIÓN A AWS ===
# 1. Subir archivos
scp -i keypair.pem stc_backup.tar.gz ubuntu@ec2-ip:~/

# 2. En EC2
tar -xzf stc_backup.tar.gz
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Restaurar BD
psql -h rds-host -U user -d db < backup_db.sql

# 4. Iniciar servicios
sudo systemctl start stc-dashboard
sudo systemctl start stc-realtime

# 5. Verificar
curl http://localhost:5000/
```

---

**Última Actualización**: 24 de Octubre, 2025
**Autor**: smarttradetecnologies-ar Team
**Soporte**: Ver SISTEMA_COMPLETO.md para arquitectura detallada
