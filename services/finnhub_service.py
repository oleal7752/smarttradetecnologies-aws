import finnhub
import os
from datetime import datetime, timedelta
import time
from collections import deque, defaultdict
import threading
import json
import websocket

class FinnhubService:
    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY environment variable is required")
        self.client = finnhub.Client(api_key=self.api_key)
        self.symbol_map = {
            'BTCUSD': 'BINANCE:BTCUSDT',
            'BTCUSD-op': 'BINANCE:BTCUSDT',
            'ETHUSD': 'BINANCE:ETHUSDT',
            'ETHUSD-op': 'BINANCE:ETHUSDT',
            'EURUSD': 'OANDA:EUR_USD',
            'EURUSD-OTC': 'OANDA:EUR_USD',
            'EURJPY': 'OANDA:EUR_JPY',
            'EURJPY-OTC': 'OANDA:EUR_JPY',
            'GBPUSD': 'OANDA:GBP_USD',
            'GBPUSD-OTC': 'OANDA:GBP_USD',
            'USDJPY': 'OANDA:USD_JPY',
            'USDJPY-OTC': 'OANDA:USD_JPY'
        }
        self.price_history = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()
        
        self.ws = None
        self.ws_running = False
        self.ws_thread = None
        self.candle_buffer = defaultdict(lambda: {
            'M1': {'open': None, 'high': None, 'low': None, 'close': None, 'volume': 0, 'time': 0},
            'M5': {'open': None, 'high': None, 'low': None, 'close': None, 'volume': 0, 'time': 0}
        })
        self.on_candle_callback = None
        
    def _get_finnhub_symbol(self, symbol):
        base_symbol = symbol.replace('-OTC', '').replace('-op', '')
        return self.symbol_map.get(symbol, self.symbol_map.get(base_symbol, f'OANDA:{base_symbol}'))
    
    def _timeframe_to_resolution(self, timeframe):
        timeframe_map = {
            'M1': '1',
            'M5': '5',
            'M15': '15',
            'M30': '30',
            'H1': '60',
            'H4': '240',
            'D': 'D',
            'W': 'W',
            'M': 'M'
        }
        return timeframe_map.get(timeframe, '5')
    
    def get_candles(self, symbol, timeframe='M5', limit=200):
        try:
            finnhub_symbol = self._get_finnhub_symbol(symbol)
            resolution = self._timeframe_to_resolution(timeframe)
            
            end_time = int(time.time())
            
            if resolution == '1':
                start_time = end_time - (limit * 60)
            elif resolution == '5':
                start_time = end_time - (limit * 5 * 60)
            elif resolution == '15':
                start_time = end_time - (limit * 15 * 60)
            elif resolution == '30':
                start_time = end_time - (limit * 30 * 60)
            elif resolution == '60':
                start_time = end_time - (limit * 60 * 60)
            else:
                start_time = end_time - (limit * 5 * 60)
            
            print(f"🔍 Finnhub Request: {finnhub_symbol} | Resolution: {resolution} | From: {start_time} to {end_time}")
            
            response = self.client.stock_candles(
                finnhub_symbol,
                resolution,
                start_time,
                end_time
            )
            
            if response['s'] == 'no_data':
                print(f"⚠️ Finnhub: No data para {symbol}")
                return None
            
            candles = []
            for i in range(len(response['t'])):
                candle = {
                    'time': response['t'][i],
                    'open': response['o'][i],
                    'high': response['h'][i],
                    'low': response['l'][i],
                    'close': response['c'][i],
                    'volume': response['v'][i] if 'v' in response else 0
                }
                candles.append(candle)
            
            print(f"✅ Finnhub: {len(candles)} velas obtenidas para {symbol}")
            return candles[-limit:] if len(candles) > limit else candles
            
        except Exception as e:
            print(f"❌ Finnhub Error para {symbol}: {str(e)}")
            return None
    
    def get_current_price(self, symbol):
        try:
            finnhub_symbol = self._get_finnhub_symbol(symbol)
            quote = self.client.quote(finnhub_symbol)
            
            if quote and 'c' in quote:
                price_data = {
                    'symbol': symbol,
                    'price': quote['c'],
                    'change': quote.get('d', 0),
                    'percent_change': quote.get('dp', 0),
                    'high': quote.get('h', 0),
                    'low': quote.get('l', 0),
                    'open': quote.get('o', 0),
                    'previous_close': quote.get('pc', 0),
                    'timestamp': int(time.time())
                }
                
                with self.lock:
                    self.price_history[symbol].append(price_data)
                
                return price_data
            
            return None
            
        except Exception as e:
            print(f"❌ Finnhub Quote Error para {symbol}: {str(e)}")
            return None
    
    def build_synthetic_candles(self, symbol, timeframe='M5', limit=200):
        """Construye velas desde historial de precios reales en tiempo real"""
        try:
            timeframe_seconds = {
                'M1': 60,
                'M5': 300,
                'M15': 900,
                'M30': 1800,
                'H1': 3600
            }.get(timeframe, 300)
            
            with self.lock:
                history = list(self.price_history.get(symbol, []))
            
            if len(history) < 2:
                current_price = self.get_current_price(symbol)
                if current_price:
                    base_price = current_price['price']
                    current_time = int(time.time())
                    candle_time = (current_time // timeframe_seconds) * timeframe_seconds
                    
                    candle = {
                        'time': candle_time,
                        'open': base_price,
                        'high': base_price,
                        'low': base_price,
                        'close': base_price,
                        'volume': 1
                    }
                    
                    print(f"⏳ Finnhub: Recolectando datos para {symbol} (1 vela inicial)")
                    return [candle]
                else:
                    return []
            
            candles_dict = {}
            for price_data in history:
                candle_time = (price_data['timestamp'] // timeframe_seconds) * timeframe_seconds
                
                if candle_time not in candles_dict:
                    candles_dict[candle_time] = {
                        'time': candle_time,
                        'open': price_data['price'],
                        'high': price_data['price'],
                        'low': price_data['price'],
                        'close': price_data['price'],
                        'volume': 0
                    }
                else:
                    candles_dict[candle_time]['high'] = max(candles_dict[candle_time]['high'], price_data['price'])
                    candles_dict[candle_time]['low'] = min(candles_dict[candle_time]['low'], price_data['price'])
                    candles_dict[candle_time]['close'] = price_data['price']
                
                candles_dict[candle_time]['volume'] += 1
            
            candles = sorted(candles_dict.values(), key=lambda x: x['time'])
            
            candles = candles[-limit:] if len(candles) > limit else candles
            print(f"✅ Finnhub: {len(candles)} velas REALES para {symbol}")
            
            candles = sorted(candles, key=lambda x: x['time'])
            
            candles = [c for c in candles if c.get('time') and c.get('open') and c.get('high') and c.get('low') and c.get('close')]
            
            return candles
            
        except Exception as e:
            print(f"❌ Error construyendo velas sintéticas para {symbol}: {str(e)}")
            return []
    
    def _on_ws_message(self, ws, message):
        """Procesar trades WebSocket y construir velas en tiempo real"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'trade':
                for trade in data.get('data', []):
                    symbol = trade.get('s')
                    price = trade.get('p')
                    volume = trade.get('v', 0)
                    timestamp_ms = trade.get('t')
                    
                    if not all([symbol, price, timestamp_ms]):
                        continue
                    
                    internal_symbol = None
                    for internal, finnhub in self.symbol_map.items():
                        if finnhub == symbol:
                            internal_symbol = internal
                            break
                    
                    if not internal_symbol:
                        continue
                    
                    timestamp = timestamp_ms // 1000
                    self._update_ws_candle(internal_symbol, 'M1', price, volume, timestamp)
                    self._update_ws_candle(internal_symbol, 'M5', price, volume, timestamp)
        
        except Exception as e:
            print(f"❌ Error procesando mensaje Finnhub WS: {e}")
    
    def _update_ws_candle(self, symbol, timeframe, price, volume, timestamp):
        """Actualizar vela desde WebSocket"""
        timeframe_seconds = 60 if timeframe == 'M1' else 300
        candle_time = (timestamp // timeframe_seconds) * timeframe_seconds
        
        candle = self.candle_buffer[symbol][timeframe]
        
        if candle['time'] != candle_time:
            if candle['open'] is not None and self.on_candle_callback:
                completed_candle = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'time': candle['time'],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume']
                }
                self.on_candle_callback(completed_candle)
            
            candle['time'] = candle_time
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
            candle['close'] = price
            candle['volume'] = volume
        else:
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price
            candle['volume'] += volume
    
    def _on_ws_error(self, ws, error):
        print(f"❌ Finnhub WebSocket error: {error}")
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        print(f"🔌 Finnhub WebSocket cerrado")
        if self.ws_running:
            print("🔄 Reintentando conexión en 5s...")
            time.sleep(5)
            self._ws_reconnect()
    
    def _on_ws_open(self, ws):
        print("✅ Finnhub WebSocket conectado")
        unique_symbols = set(self.symbol_map.values())
        for symbol in unique_symbols:
            try:
                ws.send(json.dumps({'type': 'subscribe', 'symbol': symbol}))
                print(f"📡 Suscrito a {symbol}")
            except Exception as e:
                print(f"❌ Error suscribiendo a {symbol}: {e}")
    
    def _ws_reconnect(self):
        if not self.ws_running:
            return
        try:
            self.ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={self.api_key}",
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            self.ws.run_forever()
        except Exception as e:
            print(f"❌ Error reconectando Finnhub WS: {e}")
            if self.ws_running:
                time.sleep(5)
                self._ws_reconnect()
    
    def start_websocket(self, on_candle_callback=None):
        """Iniciar WebSocket para streaming en tiempo real"""
        if self.ws_running:
            print("⚠️  Finnhub WebSocket ya activo")
            return False
        
        self.on_candle_callback = on_candle_callback
        self.ws_running = True
        
        self.ws_thread = threading.Thread(target=self._ws_connect_thread, daemon=True)
        self.ws_thread.start()
        
        print("🚀 Finnhub WebSocket iniciado")
        return True
    
    def _ws_connect_thread(self):
        try:
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={self.api_key}",
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            self.ws.run_forever()
        except Exception as e:
            print(f"❌ Error en Finnhub WebSocket thread: {e}")
    
    def stop_websocket(self):
        self.ws_running = False
        if self.ws:
            self.ws.close()
        print("🛑 Finnhub WebSocket detenido")
    
    def get_current_ws_candle(self, symbol, timeframe='M5'):
        """Obtener vela actual desde WebSocket"""
        if symbol not in self.candle_buffer:
            return None
        
        candle = self.candle_buffer[symbol].get(timeframe)
        if not candle or candle['open'] is None:
            return None
        
        return {
            'time': candle['time'],
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'volume': candle['volume']
        }

finnhub_service = FinnhubService()
