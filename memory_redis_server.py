#!/usr/bin/env python3
"""
Servidor Redis en memoria simple para pruebas
Simula las funciones básicas de Redis que necesita el sistema
"""

import time
import threading
import json
from datetime import datetime
from collections import defaultdict, deque
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse

class MemoryRedis:
    def __init__(self):
        self.data = {}
        self.lists = defaultdict(deque)
        self.lock = threading.Lock()
        print(f"[MemoryRedis] Servidor iniciado - {datetime.now()}")
    
    def set(self, key, value):
        with self.lock:
            self.data[key] = str(value)
            print(f"[MemoryRedis] SET {key} = {value}")
    
    def get(self, key):
        with self.lock:
            return self.data.get(key)
    
    def lpush(self, key, *values):
        with self.lock:
            for value in values:
                self.lists[key].appendleft(str(value))
                print(f"[MemoryRedis] LPUSH {key} <- {value}")
    
    def lpop(self, key):
        with self.lock:
            try:
                value = self.lists[key].popleft()
                print(f"[MemoryRedis] LPOP {key} -> {value}")
                return value
            except IndexError:
                return None
    
    def rpush(self, key, *values):
        with self.lock:
            for value in values:
                self.lists[key].append(str(value))
                print(f"[MemoryRedis] RPUSH {key} <- {value}")
    
    def llen(self, key):
        with self.lock:
            return len(self.lists[key])
    
    def keys(self, pattern="*"):
        with self.lock:
            all_keys = list(self.data.keys()) + list(self.lists.keys())
            if pattern == "*":
                return all_keys
            # Implementación simple de pattern matching
            return [k for k in all_keys if pattern.replace("*", "") in k]
    
    def delete(self, *keys):
        with self.lock:
            count = 0
            for key in keys:
                if key in self.data:
                    del self.data[key]
                    count += 1
                if key in self.lists:
                    del self.lists[key]
                    count += 1
            return count
    
    def flushall(self):
        with self.lock:
            self.data.clear()
            self.lists.clear()
            print("[MemoryRedis] FLUSHALL - Base de datos limpiada")

# Instancia global de Redis
memory_redis = MemoryRedis()

class RedisHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parsear comando Redis simple
            data = json.loads(post_data)
            command = data.get('command', '').upper()
            args = data.get('args', [])
            
            result = None
            
            if command == 'SET' and len(args) >= 2:
                memory_redis.set(args[0], args[1])
                result = "OK"
            elif command == 'GET' and len(args) >= 1:
                result = memory_redis.get(args[0])
            elif command == 'LPUSH' and len(args) >= 2:
                result = memory_redis.lpush(args[0], *args[1:])
            elif command == 'LPOP' and len(args) >= 1:
                result = memory_redis.lpop(args[0])
            elif command == 'RPUSH' and len(args) >= 2:
                result = memory_redis.rpush(args[0], *args[1:])
            elif command == 'LLEN' and len(args) >= 1:
                result = memory_redis.llen(args[0])
            elif command == 'KEYS' and len(args) >= 1:
                result = memory_redis.keys(args[0])
            elif command == 'DEL' and len(args) >= 1:
                result = memory_redis.delete(*args)
            elif command == 'FLUSHALL':
                memory_redis.flushall()
                result = "OK"
            else:
                result = f"ERR unknown command '{command}'"
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = json.dumps({"result": result})
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"[MemoryRedis] Error: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suprimir logs HTTP

def start_memory_redis_server():
    """Inicia el servidor Redis en memoria"""
    print("🗄️ Iniciando servidor Redis en memoria...")
    print("   Puerto: 6380 (simulado)")
    print("   Funciones: SET, GET, LPUSH, LPOP, RPUSH, LLEN, KEYS, DEL")
    
    # Simular datos iniciales
    memory_redis.set("server_status", "running")
    memory_redis.set("last_update", time.time())
    
    print("✅ Servidor Redis en memoria iniciado correctamente")
    print("   Datos de prueba creados")
    
    # Mantener el servidor corriendo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor Redis en memoria...")

if __name__ == "__main__":
    start_memory_redis_server()
