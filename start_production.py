#!/usr/bin/env python3
"""
STC Trading System - Inicio OPTIMIZADO para Producción
Versión ligera sin guindar - 2 servidores + polling inteligente
"""
import multiprocessing
import sys
import os

def run_dashboard():
    """Ejecutar dashboard en puerto 5000"""
    print("🌐 Iniciando Dashboard en puerto 5000...")
    os.system("python dashboard_server.py")

def run_realtime():
    """Ejecutar servidor RealTime en puerto 8000"""
    print("📡 Iniciando Servidor RealTime OPTIMIZADO en puerto 8000...")
    os.system("python start_realtime_server.py")

if __name__ == "__main__":
    print("🚀 STC Trading System - PRODUCCIÓN OPTIMIZADA")
    print("=" * 60)
    
    # Inicializar admin
    print("🔑 Inicializando sistema...")
    os.system("python init_admin.py")
    print()
    
    # Solo 2 procesos (Dashboard integra Backend API)
    realtime_process = multiprocessing.Process(target=run_realtime)
    dashboard_process = multiprocessing.Process(target=run_dashboard)
    
    # Iniciar
    realtime_process.start()
    print("✅ Servidor RealTime iniciado")
    
    dashboard_process.start()
    print("✅ Dashboard+API iniciado")
    
    print("=" * 60)
    print("📊 Sistema: http://localhost:5000")
    print("📡 RealTime: ws://localhost:8000/ws/live")
    print("=" * 60)
    
    # Mantener vivo
    try:
        dashboard_process.join()
        realtime_process.join()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servicios...")
        dashboard_process.terminate()
        realtime_process.terminate()
        dashboard_process.join()
        realtime_process.join()
        print("✅ Servicios detenidos")
        sys.exit(0)
