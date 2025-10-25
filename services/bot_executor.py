"""
Bot Executor - Ejecuta bots de trading en la cuenta del usuario
Los bots operan EN LA CUENTA del usuario (multi-tenant)
"""

import psycopg2
import os
import json
import threading
import time
from datetime import datetime

class BotExecutor:
    def __init__(self, account_manager):
        self.db_url = os.getenv('DATABASE_URL')
        self.account_manager = account_manager
        self.active_bots = {}  # {bot_id: thread}
        self.lock = threading.Lock()
    
    def get_connection(self):
        """Obtener conexión a PostgreSQL"""
        return psycopg2.connect(self.db_url)
    
    def get_user_bots(self, user_id):
        """Obtener bots activos del usuario"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = """
                SELECT id, name, strategy, symbol, timeframe, amount, 
                       martingale_enabled, stop_loss, take_profit, config
                FROM bots
                WHERE user_id = %s AND active = true
            """
            
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            
            bots = []
            for row in rows:
                bots.append({
                    'id': row[0],
                    'name': row[1],
                    'strategy': row[2],
                    'symbol': row[3],
                    'timeframe': row[4],
                    'amount': float(row[5]),
                    'martingale_enabled': row[6],
                    'stop_loss': float(row[7]) if row[7] else None,
                    'take_profit': float(row[8]) if row[8] else None,
                    'config': json.loads(row[9]) if row[9] else {}
                })
            
            cur.close()
            conn.close()
            
            return bots
            
        except Exception as e:
            print(f"❌ Error obteniendo bots del usuario {user_id}: {e}")
            return []
    
    def execute_bot(self, bot_id, user_id, strategy_engine, candle_service):
        """
        Ejecutar bot en loop (thread independiente)
        El bot opera EN LA CUENTA del usuario
        """
        print(f"🤖 Bot {bot_id} iniciado para usuario {user_id}")
        
        while bot_id in self.active_bots:
            try:
                # Obtener configuración del bot
                bots = self.get_user_bots(user_id)
                bot_config = next((b for b in bots if b['id'] == bot_id), None)
                
                if not bot_config:
                    print(f"⚠️  Bot {bot_id} no encontrado o inactivo")
                    break
                
                # Obtener cuenta del usuario
                account = self.account_manager.get_account(user_id, 'iqoption')
                
                if not account or not account.connected:
                    print(f"⚠️  Usuario {user_id} no conectado, bot pausado")
                    time.sleep(10)
                    continue
                
                # Obtener velas desde BD
                candles = candle_service.get_candles(
                    bot_config['symbol'],
                    bot_config['timeframe'],
                    limit=100
                )
                
                if not candles or len(candles) < 20:
                    print(f"⚠️  No hay suficientes velas para bot {bot_id}")
                    time.sleep(5)
                    continue
                
                # Ejecutar estrategia
                signal = strategy_engine.execute_strategy(
                    bot_config['strategy'],
                    candles,
                    bot_config
                )
                
                if signal and signal.get('direction'):
                    # Ejecutar orden en la cuenta del usuario
                    result = account.place_order(
                        bot_config['symbol'],
                        signal['direction'],
                        bot_config['amount'],
                        duration=1
                    )
                    
                    if result.get('success'):
                        # Guardar trade en BD
                        self.save_trade(user_id, bot_id, result, signal)
                        print(f"✅ Bot {bot_id} ejecutó {signal['direction']} en cuenta de usuario {user_id}")
                
                # Esperar según timeframe
                sleep_time = self.get_sleep_time(bot_config['timeframe'])
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Error en bot {bot_id}: {e}")
                time.sleep(10)
        
        print(f"🛑 Bot {bot_id} detenido")
    
    def get_sleep_time(self, timeframe):
        """Calcular tiempo de espera según timeframe"""
        timeframe_seconds = {
            'M1': 60,
            'M5': 300,
            'M15': 900,
            'M30': 1800,
            'H1': 3600
        }
        return timeframe_seconds.get(timeframe, 60)
    
    def save_trade(self, user_id, bot_id, order_result, signal):
        """Guardar trade en BD con user_id y bot_id"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = """
                INSERT INTO trades (
                    user_id, bot_id, symbol, direction, amount, 
                    entry_price, profit_loss, status, broker, signal_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cur.execute(query, (
                user_id,
                bot_id,  # Si es None = manual, si tiene valor = automático
                order_result.get('symbol'),
                order_result.get('direction'),
                order_result.get('amount'),
                signal.get('price', 0),
                0,  # Profit se actualiza después
                'pending',
                'iqoption',
                json.dumps(signal)
            ))
            
            trade_id = cur.fetchone()[0]
            conn.commit()
            
            cur.close()
            conn.close()
            
            print(f"💾 Trade {trade_id} guardado para usuario {user_id} (bot {bot_id})")
            
        except Exception as e:
            print(f"❌ Error guardando trade: {e}")
    
    def start_bot(self, bot_id, user_id, strategy_engine, candle_service):
        """Iniciar bot en thread separado"""
        with self.lock:
            if bot_id in self.active_bots:
                print(f"⚠️  Bot {bot_id} ya está activo")
                return False
            
            thread = threading.Thread(
                target=self.execute_bot,
                args=(bot_id, user_id, strategy_engine, candle_service),
                daemon=True
            )
            thread.start()
            
            self.active_bots[bot_id] = thread
            print(f"🚀 Bot {bot_id} iniciado para usuario {user_id}")
            return True
    
    def stop_bot(self, bot_id):
        """Detener bot"""
        with self.lock:
            if bot_id in self.active_bots:
                del self.active_bots[bot_id]
                print(f"🛑 Bot {bot_id} detenido")
                return True
            return False
    
    def stop_all_user_bots(self, user_id):
        """Detener todos los bots de un usuario"""
        bots = self.get_user_bots(user_id)
        for bot in bots:
            self.stop_bot(bot['id'])


# Se instancia cuando se necesita (requiere account_manager)
