#!/usr/bin/env python3
"""
🔧 POST-INSTALACIÓN STC TRADING SYSTEM
Configura el entorno después de la instalación inicial
"""
import os
import subprocess
import sys
from pathlib import Path
import json

def post_install_setup():
    """Configuración post-instalación"""
    
    print("🔧 POST-INSTALACIÓN STC TRADING SYSTEM")
    print("=" * 50)
    
    project_dir = Path.cwd()
    print(f"📁 Directorio del proyecto: {project_dir}")
    
    # 1. Verificar Python
    print("\n1️⃣ VERIFICANDO PYTHON...")
    python_version = sys.version
    print(f"   🐍 Python {python_version}")
    
    if sys.version_info < (3, 8):
        print("   ❌ Se requiere Python 3.8+")
        return False
    
    # 2. Crear entorno virtual si no existe
    print("\n2️⃣ CONFIGURANDO ENTORNO VIRTUAL...")
    venv_path = project_dir / ".venv311"
    
    if not venv_path.exists():
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            print(f"   ✅ Entorno virtual creado: {venv_path}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error creando entorno virtual: {e}")
            return False
    else:
        print(f"   ✅ Entorno virtual existente: {venv_path}")
    
    # 3. Verificar requirements.txt
    print("\n3️⃣ VERIFICANDO DEPENDENCIAS...")
    req_file = project_dir / "requirements.txt"
    
    if req_file.exists():
        print("   ✅ requirements.txt encontrado")
        # Leer dependencias
        with open(req_file, 'r', encoding='utf-8') as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"   📦 {len(deps)} dependencias listadas")
    else:
        print("   ⚠️ requirements.txt no encontrado")
    
    # 4. Verificar estructura de directorios
    print("\n4️⃣ VERIFICANDO ESTRUCTURA...")
    required_dirs = [
        "templates", "static/js", "static/css", "static/charts",
        "data", "logs", "tests", "docs", "config"
    ]
    
    for dir_name in required_dirs:
        dir_path = project_dir / dir_name
        if dir_path.exists():
            print(f"   ✅ {dir_name}/")
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   🔧 Creado: {dir_name}/")
    
    # 5. Verificar archivos esenciales
    print("\n5️⃣ VERIFICANDO ARCHIVOS ESENCIALES...")
    essential_files = [
        "iq_routes_redis_patch.py",
        "signals_service_redis.py",
        "templates/dashboard.html",
        ".env.example",
        "static/js/tradingview-config.js"
    ]
    
    missing_files = []
    for file_name in essential_files:
        file_path = project_dir / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ Falta: {file_name}")
            missing_files.append(file_name)
    
    # 6. Verificar TradingView Charts
    print("\n6️⃣ VERIFICANDO TRADINGVIEW CHARTS...")
    charts_dir = project_dir / "lightweight-charts"
    
    if charts_dir.exists():
        print("   ✅ Directorio lightweight-charts encontrado")
        # Verificar archivos principales
        main_files = ["package.json", "dist", "src"]
        for file_name in main_files:
            file_path = charts_dir / file_name
            if file_path.exists():
                print(f"   ✅ {file_name}")
            else:
                print(f"   ⚠️ No encontrado: {file_name}")
    else:
        print("   ❌ Directorio lightweight-charts no encontrado")
        print("   🔧 Ejecutar: git clone https://github.com/tradingview/lightweight-charts.git")
    
    # 7. Crear configuración de logging
    print("\n7️⃣ CONFIGURANDO LOGGING...")
    create_logging_config(project_dir)
    
    # 8. Crear script de inicio
    print("\n8️⃣ CREANDO SCRIPTS DE INICIO...")
    create_startup_scripts(project_dir)
    
    # 9. Resumen final
    print(f"\n🎯 POST-INSTALACIÓN COMPLETADA")
    
    if missing_files:
        print(f"\n⚠️ ARCHIVOS FALTANTES ({len(missing_files)}):")
        for file in missing_files:
            print(f"   - {file}")
    
    print("\n🔧 PRÓXIMOS PASOS:")
    print("1. Copiar .env.example a .env y configurar credenciales")
    print("2. Activar entorno virtual:")
    print("   - Windows: .venv311\\Scripts\\activate")
    print("   - Linux/Mac: source .venv311/bin/activate") 
    print("3. Instalar dependencias: pip install -r requirements.txt")
    print("4. Ejecutar verificación: python verify_system.py")
    
    return len(missing_files) == 0

def create_logging_config(project_dir):
    """Crear configuración de logging"""
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/stc_trading.log",
                "mode": "a"
            }
        },
        "loggers": {
            "stc_trading": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
    
    config_path = project_dir / "config" / "logging.json"
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(logging_config, f, indent=2)
    
    print(f"   ✅ Configuración de logging: config/logging.json")

def create_startup_scripts(project_dir):
    """Crear scripts de inicio"""
    
    # Script de inicio Windows
    windows_script = """@echo off
echo ================================================
echo 🚀 INICIANDO STC TRADING SYSTEM
echo ================================================

REM Activar entorno virtual
call .venv311\\Scripts\\activate.bat

REM Verificar que estamos en el directorio correcto
if not exist "iq_routes_redis_patch.py" (
    echo ❌ Error: No se encuentra iq_routes_redis_patch.py
    echo Asegúrate de ejecutar desde el directorio del proyecto
    pause
    exit /b 1
)

REM Iniciar servicios
echo 🔧 Iniciando servicios STC Trading...

REM Iniciar servidor principal
start "STC Trading Server" python iq_routes_redis_patch.py

REM Iniciar servicio de señales
start "Signals Service" python signals_service_redis.py

echo ✅ Servicios iniciados
echo 🌐 Dashboard: http://localhost:5001
echo 📊 Para detener: Cerrar ventanas de terminal

pause
"""
    
    script_path = project_dir / "start_stc_complete.bat"
    script_path.write_text(windows_script, encoding='utf-8')
    print(f"   ✅ Script de inicio: start_stc_complete.bat")
    
    # Script de verificación
    verify_script = """#!/usr/bin/env python3
import sys
import os
from pathlib import Path

def verify_system():
    print("🔍 VERIFICANDO SISTEMA STC TRADING")
    print("=" * 40)
    
    errors = []
    warnings = []
    
    # Verificar archivos esenciales
    essential_files = [
        "iq_routes_redis_patch.py",
        "signals_service_redis.py", 
        "templates/dashboard.html",
        ".env.example"
    ]
    
    for file in essential_files:
        if not Path(file).exists():
            errors.append(f"Archivo faltante: {file}")
    
    # Verificar directorios
    dirs = ["templates", "static", "data", "logs", "tests"]
    for dir_name in dirs:
        if not Path(dir_name).exists():
            errors.append(f"Directorio faltante: {dir_name}")
    
    # Verificar entorno virtual
    if not Path(".venv311").exists():
        warnings.append("Entorno virtual no configurado (.venv311)")
    
    # Verificar .env
    if not Path(".env").exists():
        warnings.append("Archivo .env no configurado (usar .env.example)")
    
    # Mostrar resultados
    if errors:
        print("❌ ERRORES:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("⚠️ ADVERTENCIAS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("✅ SISTEMA VERIFICADO CORRECTAMENTE")
        return True
    
    return len(errors) == 0

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)
"""
    
    verify_path = project_dir / "verify_system.py"
    verify_path.write_text(verify_script, encoding='utf-8')
    print(f"   ✅ Script de verificación: verify_system.py")

if __name__ == "__main__":
    success = post_install_setup()
    if success:
        print("\n🎉 ¡POST-INSTALACIÓN EXITOSA!")
    else:
        print("\n⚠️ Post-instalación completada con advertencias")
