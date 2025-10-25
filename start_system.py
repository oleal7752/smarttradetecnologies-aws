#!/usr/bin/env python3
"""
STC Trading System - Inicio Unificado
Inicia dashboard (puerto 5000) y backend API (puerto 5002) en paralelo
"""
import multiprocessing
import sys
import os

def run_dashboard():
    """Ejecutar dashboard en puerto 5000"""
    print("🌐 Iniciando Dashboard en puerto 5000...")
    os.system("python dashboard_server.py")

def run_backend():
    """Ejecutar backend API en puerto 5002"""
    print("⚙️ Iniciando Backend API en puerto 5002...")
    os.system("python iq_routes_redis_patch.py")

def run_realtime():
    """Ejecutar servidor RealTime en puerto 8000"""
    print("📡 Iniciando Servidor RealTime en puerto 8000...")
    os.system("python start_realtime_server.py")

if __name__ == "__main__":
    print("🚀 STC Trading System - Iniciando servicios...")
    print("=" * 60)
    
    # Inicializar admin (crear si no existe)
    print("🔑 Inicializando usuario administrador...")
    os.system("python init_admin.py")
    print()
    
    # Crear procesos para TRES servidores
    dashboard_process = multiprocessing.Process(target=run_dashboard)
    backend_process = multiprocessing.Process(target=run_backend)
    realtime_process = multiprocessing.Process(target=run_realtime)
    
    # Iniciar todos los procesos
    backend_process.start()
    print("✅ Backend API iniciado")
    
    realtime_process.start()
    print("✅ Servidor RealTime iniciado")
    
    dashboard_process.start()
    print("✅ Dashboard iniciado")
    
    print("=" * 60)
    print("📊 Dashboard: http://localhost:5000")
    print("🔧 Backend API: http://localhost:5002")
    print("📡 RealTime WS: ws://localhost:8000/ws/live")
    print("=" * 60)
    
    # Esperar a que terminen (mantener el proceso principal vivo)
    try:
        dashboard_process.join()
        backend_process.join()
        realtime_process.join()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servicios...")
        dashboard_process.terminate()
        backend_process.terminate()
        realtime_process.terminate()
        dashboard_process.join()
        backend_process.join()
        realtime_process.join()
        print("✅ Servicios detenidos")
        sys.exit(0)
