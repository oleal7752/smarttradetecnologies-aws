#!/usr/bin/env python3
"""
🔧 STC Trading System - Configuración Post-Instalación
Ejecuta este script después de copiar los archivos del sistema
"""
import os
import shutil
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Mostrar banner del sistema"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    🚀 STC TRADING SYSTEM 🚀                       ║
║                   Configuración Post-Instalación                   ║
╚════════════════════════════════════════════════════════════════════╝
""")

def check_python_version():
    """Verificar versión de Python"""
    print("🐍 Verificando Python...")
    version = sys.version_info
    
    if version.major != 3 or version.minor < 8:
        print(f"❌ Python {version.major}.{version.minor} detectado")
        print("   Se requiere Python 3.8 o superior")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True

def setup_environment_file():
    """Configurar archivo .env"""
    print("\n⚙️ Configurando archivo .env...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print("✅ Archivo .env creado desde .env.example")
        else:
            print("⚠️ No se encontró .env.example, creando .env básico...")
            create_basic_env_file()
    else:
        print("✅ Archivo .env ya existe")
    
    print("⚠️  IMPORTANTE: Edita .env con tus credenciales IQ Option reales")
    print("   - IQ_EMAIL=tu_email@gmail.com")
    print("   - IQ_PASSWORD=tu_password")

def create_basic_env_file():
    """Crear archivo .env básico"""
    basic_env = """# STC Trading System - Variables de Entorno
SERVER_BASE=http://127.0.0.1:5002
SERVER_PORT=5001
API_PORT=5002

# Credenciales IQ Option (CONFIGURAR)
IQ_EMAIL=tu_email@gmail.com
IQ_PASSWORD=tu_password
IQ_BALANCE_TYPE=PRACTICE

# Configuración de trading
IQ_SYMBOLS=EURUSD-OTC,GBPUSD-OTC
IQ_TIMEFRAMES=M1,M5
IQ_PUSH_INTERVAL_SEC=1.0

# Sistema
HTTP_TIMEOUT=4.0
LOG_LEVEL=INFO
REDIS_URL=redis://127.0.0.1:6380/0
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(basic_env)

def create_directories():
    """Crear directorios necesarios"""
    print("\n📁 Creando estructura de directorios...")
    
    directories = [
        "logs",
        "data", 
        "static/js",
        "static/css",
        "templates",
        "tests",
        "docs",
        "config"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}/")
        else:
            print(f"   ℹ️  {directory}/ (ya existe)")

def check_requirements():
    """Verificar archivo requirements.txt"""
    print("\n📦 Verificando requirements.txt...")
    
    req_file = Path("requirements.txt")
    if req_file.exists():
        print("✅ requirements.txt encontrado")
        return True
    else:
        print("⚠️ requirements.txt no encontrado, creando básico...")
        create_basic_requirements()
        return True

def create_basic_requirements():
    """Crear requirements.txt básico"""
    basic_requirements = """# STC Trading System - Dependencias Python

# Framework Web
Flask==2.3.3
flask-cors==4.0.0

# Base de datos y cache  
redis==5.0.1

# HTTP y requests
httpx==0.25.0
requests==2.31.0

# IQ Option API
iqoptionapi==5.0.0

# Utilidades
python-dotenv==1.0.0
websocket-client==1.6.4

# Opcional - Para análisis
pandas==2.1.1
numpy==1.24.3
"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(basic_requirements)

def install_dependencies():
    """Instalar dependencias Python"""
    print("\n📥 Instalando dependencias...")
    
    try:
        # Intentar usar pip del entorno virtual primero
        venv_paths = [
            ".venv311/Scripts/pip.exe",
            "venv/Scripts/pip.exe", 
            ".venv/bin/pip",
            "venv/bin/pip"
        ]
        
        pip_cmd = "pip"
        for venv_pip in venv_paths:
            if Path(venv_pip).exists():
                pip_cmd = venv_pip
                print(f"   🐍 Usando pip del entorno virtual: {venv_pip}")
                break
        
        # Instalar dependencias
        result = subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencias instaladas correctamente")
            return True
        else:
            print(f"❌ Error instalando dependencias:")
            print(f"   {result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error ejecutando pip: {e}")
        print("   Instala manualmente: pip install -r requirements.txt")
        return False

def check_docker():
    """Verificar Docker para Redis"""
    print("\n🐳 Verificando Docker...")
    
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Docker disponible")
            
            # Verificar docker-compose
            try:
                result2 = subprocess.run(["docker-compose", "--version"], 
                                       capture_output=True, text=True, timeout=5)
                if result2.returncode == 0:
                    print("✅ Docker Compose disponible")
                    return True
                else:
                    print("⚠️ Docker Compose no disponible")
                    return False
            except:
                print("⚠️ Docker Compose no disponible")
                return False
        else:
            print("⚠️ Docker no disponible")
            return False
            
    except:
        print("⚠️ Docker no instalado")
        return False

def verify_system():
    """Verificar sistema completo"""
    print("\n🔍 Verificando sistema...")
    
    # Verificar archivos esenciales
    essential_files = [
        "iq_routes_redis_patch.py",
        "iq_client.py", 
        "mt5_server.py",
        "requirements.txt",
        ".env"
    ]
    
    missing_files = []
    for file_path in essential_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - FALTANTE")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️ Archivos faltantes: {len(missing_files)}")
        print("   Copia los archivos faltantes antes de continuar")
        return False
    else:
        print("\n✅ Todos los archivos esenciales presentes")
        return True

def create_start_script():
    """Crear script de inicio si no existe"""
    print("\n🚀 Verificando script de inicio...")
    
    start_scripts = ["start_stc_system.bat", "start_iq_system_complete.bat"]
    
    for script in start_scripts:
        if Path(script).exists():
            print(f"✅ Script de inicio encontrado: {script}")
            return
    
    print("⚠️ No se encontró script de inicio, usar comando manual:")
    print("   Windows: start_stc_system.bat")
    print("   Linux/Mac: python iq_routes_redis_patch.py &")

def show_next_steps():
    """Mostrar próximos pasos"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                        🎯 PRÓXIMOS PASOS                          ║
╚════════════════════════════════════════════════════════════════════╝

1. 📝 CONFIGURAR CREDENCIALES:
   - Edita el archivo .env
   - Cambia IQ_EMAIL por tu email real
   - Cambia IQ_PASSWORD por tu contraseña real

2. 🗄️ INICIAR REDIS:
   - Con Docker: docker-compose up -d
   - O instalar Redis nativo en puerto 6380

3. 🚀 INICIAR SISTEMA:
   - Windows: start_stc_system.bat
   - Linux/Mac: ./start_system.sh

4. 🌐 ACCEDER AL DASHBOARD:
   - Abre http://localhost:5001 en tu navegador
   - Haz login con tus credenciales IQ Option

5. 🧪 VERIFICAR FUNCIONAMIENTO:
   - python tests/test_symbols.py
   - python tests/test_complete_system.py

╔════════════════════════════════════════════════════════════════════╗
║  ⚠️ IMPORTANTE: Usa PRACTICE para pruebas, REAL solo en producción ║
╚════════════════════════════════════════════════════════════════════╝
""")

def main():
    """Función principal"""
    print_banner()
    
    # Verificaciones
    if not check_python_version():
        return False
    
    # Configuración
    setup_environment_file()
    create_directories()
    check_requirements()
    
    # Instalación
    deps_ok = install_dependencies()
    
    # Verificaciones finales
    docker_ok = check_docker()
    system_ok = verify_system()
    create_start_script()
    
    # Mostrar resultados
    print("\n" + "="*70)
    print("📋 RESUMEN DE CONFIGURACIÓN:")
    print("="*70)
    print(f"🐍 Python:        {'✅' if True else '❌'}")
    print(f"📦 Dependencias:  {'✅' if deps_ok else '⚠️'}")
    print(f"🐳 Docker:        {'✅' if docker_ok else '⚠️'}")
    print(f"📁 Archivos:      {'✅' if system_ok else '❌'}")
    
    if system_ok and deps_ok:
        print("\n🎉 CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        show_next_steps()
        return True
    else:
        print("\n⚠️ CONFIGURACIÓN PARCIAL - Revisar errores arriba")
        return False

if __name__ == "__main__":
    success = main()
    
    print("\nPresiona Enter para continuar...")
    input()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
