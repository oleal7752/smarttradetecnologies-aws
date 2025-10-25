#!/usr/bin/env python3
"""
Script para iniciar el servidor de trading en tiempo real
"""
import uvicorn
from realtime_trading.realtime_server import app

if __name__ == "__main__":
    print("🚀 Iniciando servidor de trading en tiempo real...")
    print("📡 WebSocket: ws://0.0.0.0:8000/ws/live")
    print("🔗 API Status: http://0.0.0.0:8000/api/status")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )
