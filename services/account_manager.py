"""
Account Manager - Gestión de cuentas de trading por usuario
Soporta múltiples brokers: IQ Option, MT5, OlympTrade
"""

import psycopg2
import os
import json
import threading

class BrokerAccount:
    """Clase base para cuentas de broker"""
    
    def __init__(self, user_id, credentials):
        self.user_id = user_id
        self.credentials = credentials
        self.connected = False
        self.balance = 0
    
    def connect(self):
        """Conectar a la cuenta del broker"""
        raise NotImplementedError
    
    def get_balance(self):
        """Obtener balance actual"""
        raise NotImplementedError
    
    def place_order(self, symbol, direction, amount, duration=1):
        """Ejecutar orden"""
        raise NotImplementedError
    
    def disconnect(self):
        """Desconectar"""
        raise NotImplementedError


class IQOptionAccount(BrokerAccount):
    """Cuenta de IQ Option individual por usuario"""
    
    def __init__(self, user_id, email, password, account_type='PRACTICE'):
        super().__init__(user_id, {'email': email, 'password': password})
        self.email = email
        self.password = password
        self.account_type = account_type
        self.api = None
    
    def connect(self):
        """Conectar a IQ Option con credenciales del usuario usando timeout"""
        try:
            connection_result = {'check': False, 'reason': 'timeout', 'api': None}
            
            def try_connect():
                try:
                    from iqoptionapi.stable_api import IQ_Option
                    api_client = IQ_Option(self.email, self.password)
                    check, reason = api_client.connect()
                    connection_result['check'] = check
                    connection_result['reason'] = reason
                    connection_result['api'] = api_client
                except ImportError as e:
                    connection_result['check'] = False
                    connection_result['reason'] = f"iqoptionapi no disponible: {e}"
                except Exception as e:
                    connection_result['check'] = False
                    connection_result['reason'] = str(e)
            
            connect_thread = threading.Thread(target=try_connect)
            connect_thread.start()
            connect_thread.join(timeout=15)
            
            if connect_thread.is_alive():
                print(f"❌ Timeout conectando usuario {self.user_id} a IQ Option (>15s)")
                return False
            
            if connection_result['check']:
                self.api = connection_result['api']
                self.api.change_balance(self.account_type)
                self.connected = True
                self.balance = self.api.get_balance()
                print(f"✅ Usuario {self.user_id} conectado a IQ Option ({self.account_type})")
                return True
            else:
                print(f"❌ Error conectando usuario {self.user_id}: {connection_result['reason']}")
                return False
                
        except Exception as e:
            print(f"❌ Excepción conectando usuario {self.user_id}: {e}")
            return False
    
    def get_balance(self):
        """Obtener balance actual"""
        if not self.connected or not self.api:
            return 0
        
        try:
            self.balance = self.api.get_balance()
            return self.balance
        except Exception as e:
            print(f"❌ Error obteniendo balance usuario {self.user_id}: {e}")
            return 0
    
    def place_order(self, symbol, direction, amount, duration=1):
        """Ejecutar orden en la cuenta del usuario"""
        if not self.connected or not self.api:
            return {"success": False, "error": "No conectado"}
        
        try:
            action = "call" if direction.upper() == "CALL" else "put"
            
            print(f"📤 Enviando orden: {action.upper()} {symbol} ${amount} {duration}min")
            
            # Intentar Binary/Turbo primero
            status, order_id = self.api.buy(amount, symbol, action, duration)
            
            # Si Binary falla con "suspended", intentar Digital Options
            if not status and isinstance(order_id, str) and "suspended" in order_id.lower():
                print(f"⚠️ Binary/Turbo cerrado, intentando Digital Options...")
                status, order_id = self.api.buy_digital_spot(symbol, amount, action, duration)
            
            print(f"📥 Respuesta IQ Option: status={status}, order_id={order_id}")
            
            if status:
                print(f"✅ Orden ejecutada exitosamente. ID: {order_id}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "user_id": self.user_id,
                    "symbol": symbol,
                    "direction": direction,
                    "amount": amount,
                    "message": f"Orden ejecutada. ID: {order_id}"
                }
            else:
                error_msg = f"Orden rechazada por IQ Option. Respuesta: {order_id}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error ejecutando orden: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def disconnect(self):
        """Desconectar"""
        try:
            if self.api:
                self.api.close()
            self.connected = False
            print(f"🔌 Usuario {self.user_id} desconectado de IQ Option")
        except Exception as e:
            print(f"❌ Error desconectando usuario {self.user_id}: {e}")
    
    def start_candle_stream(self, symbol, timeframe='M5', maxdict=100):
        """
        Iniciar streaming en tiempo real de velas
        timeframe: 'M1', 'M5', etc.
        maxdict: máximo de velas a mantener en memoria
        """
        if not self.connected or not self.api:
            print(f"❌ Usuario {self.user_id} no conectado - no se puede iniciar stream")
            return False
        
        try:
            # Convertir timeframe a segundos
            timeframe_map = {
                'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800,
                'H1': 3600, 'H4': 14400, 'D1': 86400
            }
            
            size = timeframe_map.get(timeframe, 300)  # Default M5
            
            print(f"📡 Iniciando stream de velas para usuario {self.user_id}: {symbol} {timeframe} ({size}s)")
            self.api.start_candles_stream(symbol, size, maxdict)
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando stream usuario {self.user_id}: {e}")
            return False
    
    def get_current_candle(self, symbol, timeframe='M5'):
        """
        Obtener la vela actual en tiempo real
        Retorna la última vela del stream
        """
        if not self.connected or not self.api:
            return None
        
        try:
            # Convertir timeframe a segundos
            timeframe_map = {
                'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800,
                'H1': 3600, 'H4': 14400, 'D1': 86400
            }
            
            size = timeframe_map.get(timeframe, 300)
            
            # Obtener velas en tiempo real
            candles = self.api.get_realtime_candles(symbol, size)
            
            if candles and len(candles) > 0:
                # Obtener la vela más reciente (último timestamp)
                latest_timestamp = max(candles.keys())
                latest_candle = candles[latest_timestamp]
                
                # Convertir formato IQ Option a formato interno
                return {
                    'time': int(latest_timestamp),
                    'open': float(latest_candle['open']),
                    'high': float(latest_candle['max']),
                    'low': float(latest_candle['min']),
                    'close': float(latest_candle['close']),
                    'volume': float(latest_candle.get('volume', 0))
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo vela actual usuario {self.user_id}: {e}")
            return None
    
    def stop_candle_stream(self, symbol, timeframe='M5'):
        """Detener streaming de velas"""
        if not self.connected or not self.api:
            return False
        
        try:
            timeframe_map = {
                'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800,
                'H1': 3600, 'H4': 14400, 'D1': 86400
            }
            
            size = timeframe_map.get(timeframe, 300)
            
            print(f"⏹️ Deteniendo stream de velas para usuario {self.user_id}: {symbol} {timeframe}")
            self.api.stop_candles_stream(symbol, size)
            return True
            
        except Exception as e:
            print(f"❌ Error deteniendo stream usuario {self.user_id}: {e}")
            return False


class MT5Account(BrokerAccount):
    """Cuenta de MT5 (implementación futura)"""
    
    def connect(self):
        print(f"⚠️  MT5 no implementado aún para usuario {self.user_id}")
        return False
    
    def get_balance(self):
        return 0
    
    def place_order(self, symbol, direction, amount, duration=1):
        return {"success": False, "error": "MT5 no implementado"}
    
    def disconnect(self):
        pass


class OlympTradeAccount(BrokerAccount):
    """Cuenta de OlympTrade (implementación futura)"""
    
    def connect(self):
        print(f"⚠️  OlympTrade no implementado aún para usuario {self.user_id}")
        return False
    
    def get_balance(self):
        return 0
    
    def place_order(self, symbol, direction, amount, duration=1):
        return {"success": False, "error": "OlympTrade no implementado"}
    
    def disconnect(self):
        pass


class AccountManager:
    """Manager central de cuentas por usuario"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.accounts = {}  # {user_id: BrokerAccount}
        self.lock = threading.Lock()
    
    def get_connection(self):
        """Obtener conexión a PostgreSQL"""
        return psycopg2.connect(self.db_url)
    
    def get_account(self, user_id, broker_type='iqoption'):
        """
        Obtener cuenta del usuario (crea si no existe)
        Cada usuario tiene su propia conexión al broker
        """
        with self.lock:
            key = f"{user_id}_{broker_type}"
            
            # Si ya existe en cache, retornar
            if key in self.accounts and self.accounts[key].connected:
                return self.accounts[key]
            
            # Obtener credenciales desde BD
            credentials = self.get_user_credentials(user_id, broker_type)
            
            if not credentials:
                print(f"⚠️  Usuario {user_id} no tiene credenciales para {broker_type}")
                return None
            
            # Crear cuenta según el broker
            if broker_type == 'iqoption':
                account = IQOptionAccount(
                    user_id,
                    credentials['email'],
                    credentials['password'],
                    credentials.get('account_type', 'PRACTICE')
                )
            elif broker_type == 'mt5':
                account = MT5Account(user_id, credentials)
            elif broker_type == 'olymptrade':
                account = OlympTradeAccount(user_id, credentials)
            else:
                print(f"❌ Broker desconocido: {broker_type}")
                return None
            
            # Conectar
            if account.connect():
                self.accounts[key] = account
                return account
            
            return None
    
    def get_user_credentials(self, user_id, broker_type):
        """Obtener credenciales del usuario desde BD"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = """
                SELECT broker_email, broker_password, account_type, broker_data
                FROM broker_accounts
                WHERE user_id = %s AND broker_name = %s AND status = 'validated'
                LIMIT 1
            """
            
            cur.execute(query, (user_id, broker_type))
            row = cur.fetchone()
            
            cur.close()
            conn.close()
            
            if row:
                return {
                    'email': row[0],
                    'password': row[1],
                    'account_type': row[2],
                    'data': json.loads(row[3]) if row[3] else {}
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo credenciales: {e}")
            return None
    
    def disconnect_user(self, user_id, broker_type='iqoption'):
        """Desconectar usuario específico"""
        with self.lock:
            key = f"{user_id}_{broker_type}"
            
            if key in self.accounts:
                self.accounts[key].disconnect()
                del self.accounts[key]
                print(f"🔌 Usuario {user_id} desconectado de {broker_type}")
    
    def disconnect_all(self):
        """Desconectar todos los usuarios"""
        with self.lock:
            for account in self.accounts.values():
                account.disconnect()
            self.accounts.clear()
            print("🔌 Todas las cuentas desconectadas")


# Instancia global
account_manager = AccountManager()
