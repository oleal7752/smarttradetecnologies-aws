"""
Pipeline específico para OlympTrade API
Maneja obtención y procesamiento de datos para TRADING en OlympTrade
"""
import os
from typing import List, Dict, Optional
from services.candle_pipeline_base import CandlePipelineBase
from services.candle_utils import SymbolMapper, TimeframeHelper

class OlympTradePipeline(CandlePipelineBase):
    """Pipeline para OlympTrade (trading)"""
    
    def __init__(self):
        super().__init__(source='olymptrade')
        self.access_token = os.getenv('OLYMPTRADE_TOKEN')
        self.client = None
        self.symbol_mapper = SymbolMapper()
        self._connected = False
    
    async def connect(self):
        """Conecta al API de OlympTrade usando olymptrade-ws"""
        if self._connected and self.client:
            return True
        
        try:
            from olymptrade_ws import OlympTradeClient
            
            if not self.access_token:
                print("⚠️ OlympTrade: TOKEN no configurado")
                return False
            
            self.client = OlympTradeClient(access_token=self.access_token)
            await self.client.start()
            
            if self.client.is_connected:
                self._connected = True
                print("✅ OlympTrade: Conectado exitosamente")
                return True
            else:
                print("❌ OlympTrade: Falló conexión")
                return False
                
        except ImportError:
            print("❌ OlympTrade: Biblioteca olymptrade-ws no instalada")
            print("   Ejecuta: pip install olymptrade-ws")
            return False
        except Exception as e:
            print(f"❌ OlympTrade Error de conexión: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta del API"""
        if self.client:
            try:
                await self.client.stop()
                self._connected = False
                print("✅ OlympTrade: Desconectado")
            except Exception as e:
                print(f"⚠️ Error desconectando OlympTrade: {e}")
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convierte timeframe a segundos para OlympTrade"""
        return TimeframeHelper.to_seconds(timeframe)
    
    def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """Obtiene velas desde OlympTrade API"""
        if not self._connected or not self.client:
            print(f"⚠️ OlympTrade: No conectado, no se pueden obtener velas de {symbol}")
            return None
        
        try:
            olymp_symbol = self.symbol_mapper.get_broker_symbol(symbol, 'olymptrade')
            seconds = self._timeframe_to_seconds(timeframe)
            
            end_time = int(TimeframeHelper.get_start_time(timeframe, 0))
            start_time = TimeframeHelper.get_start_time(timeframe, limit)
            
            print(f"🔍 OlympTrade: {olymp_symbol} | {timeframe} | {start_time} → {end_time}")
            
            candles = []
            
            print(f"⚠️ OlympTrade: API de velas históricos en desarrollo")
            print(f"   Retornando lista vacía por ahora")
            
            return candles
            
        except Exception as e:
            print(f"❌ OlympTrade Error para {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene precio actual desde OlympTrade"""
        if not self._connected or not self.client:
            return None
        
        try:
            olymp_symbol = self.symbol_mapper.get_broker_symbol(symbol, 'olymptrade')
            
            print(f"⚠️ OlympTrade: API de precio actual en desarrollo")
            
            return None
            
        except Exception as e:
            print(f"❌ OlympTrade Price Error: {e}")
            return None
    
    async def get_balance(self) -> Optional[Dict]:
        """Obtiene balance de la cuenta OlympTrade"""
        if not self._connected or not self.client:
            return None
        
        try:
            balance = await self.client.balance.get_balance()
            
            demo_acc = next((acc for acc in balance['d'] if acc['group'] == 'demo'), None)
            real_acc = next((acc for acc in balance['d'] if acc['group'] == 'real'), None)
            
            return {
                'demo': float(demo_acc['amount']) if demo_acc else 0,
                'real': float(real_acc['amount']) if real_acc else 0
            }
            
        except Exception as e:
            print(f"❌ OlympTrade Balance Error: {e}")
            return None
    
    async def execute_trade(self, symbol: str, amount: float, direction: str, duration: int, account_type: str = 'demo') -> Optional[Dict]:
        """
        Ejecuta operación en OlympTrade
        
        Args:
            symbol: Par de divisas
            amount: Monto a invertir
            direction: 'up' o 'down'
            duration: Duración en segundos
            account_type: 'demo' o 'real'
        """
        if not self._connected or not self.client:
            return {'success': False, 'error': 'No conectado a OlympTrade'}
        
        try:
            olymp_symbol = self.symbol_mapper.get_broker_symbol(symbol, 'olymptrade')
            
            balance = await self.get_balance()
            if not balance:
                return {'success': False, 'error': 'No se pudo obtener balance'}
            
            account_id = None
            
            result = await self.client.trade.place_trade(
                pair=olymp_symbol,
                amount=amount,
                direction=direction.lower(),
                duration=duration,
                account_id=account_id,
                group=account_type
            )
            
            if result:
                return {
                    'success': True,
                    'trade_id': result.get('id'),
                    'amount': amount,
                    'direction': direction,
                    'duration': duration,
                    'timestamp': int(TimeframeHelper.get_start_time('M1', 0))
                }
            else:
                return {'success': False, 'error': 'Error ejecutando trade'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
