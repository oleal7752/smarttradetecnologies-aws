"""
Service Manager - Orquestador central de servicios
Integra todos los servicios para arquitectura multi-usuario
"""

from services.candle_service import candle_service
from services.symbols_service import symbols_service
from services.account_manager import account_manager
from services.bot_executor import BotExecutor
from services.candle_worker import candle_worker

class ServiceManager:
    def __init__(self):
        self.candle_service = candle_service
        self.symbols_service = symbols_service
        self.account_manager = account_manager
        self.bot_executor = None  # Se inicializa cuando se necesita
        self.candle_worker = candle_worker
        self.initialized = False
    
    def initialize(self, strategy_engine=None):
        """Inicializar servicios"""
        if self.initialized:
            return
        
        # Inicializar bot executor con account manager
        self.bot_executor = BotExecutor(self.account_manager)
        
        print("✅ Service Manager inicializado")
        self.initialized = True
    
    def start_candle_worker(self, api_client):
        """Iniciar worker de velas en background"""
        self.candle_worker.start(api_client)
    
    def stop_candle_worker(self):
        """Detener worker de velas"""
        self.candle_worker.stop()
    
    def get_candles(self, symbol, timeframe, limit=200):
        """Obtener velas desde BD (alta disponibilidad)"""
        return self.candle_service.get_candles(symbol, timeframe, limit)
    
    def get_symbols(self, api_client=None):
        """Obtener símbolos disponibles"""
        return self.symbols_service.get_symbols(api_client)
    
    def get_user_account(self, user_id, broker='iqoption'):
        """Obtener cuenta del usuario"""
        return self.account_manager.get_account(user_id, broker)
    
    def disconnect_user(self, user_id, broker='iqoption'):
        """Desconectar usuario"""
        self.account_manager.disconnect_user(user_id, broker)
    
    def start_user_bot(self, bot_id, user_id, strategy_engine):
        """Iniciar bot del usuario"""
        if self.bot_executor:
            return self.bot_executor.start_bot(
                bot_id,
                user_id,
                strategy_engine,
                self.candle_service
            )
        return False
    
    def stop_user_bot(self, bot_id):
        """Detener bot"""
        if self.bot_executor:
            return self.bot_executor.stop_bot(bot_id)
        return False
    
    def cleanup(self):
        """Limpiar recursos"""
        self.stop_candle_worker()
        self.account_manager.disconnect_all()
        print("🧹 Servicios limpiados")


# Instancia global
service_manager = ServiceManager()
