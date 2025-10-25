"""
Bot de Trading con Sistema de Gales Duales
Maneja secuencias de CALL y PUT independientes con martingala
"""

import time
import threading
from typing import Dict, Optional, Callable, List
from dual_gale_manager import DualGaleManager
from strategy_engine import Strategy, Candle, Signal
from auto_trading_bot import BotConfig, BotStats
import uuid


class DualGaleBot:
    """
    Bot de trading con sistema de gales duales
    
    Características:
    - Secuencias CALL y PUT independientes
    - Cada secuencia con gales 0-7
    - Nuevas señales inician secuencias si no hay activa
    - No cancela secuencias en progreso
    """
    
    def __init__(
        self,
        bot_id: str,
        config: BotConfig,
        strategy: Strategy,
        trade_executor: Callable,
        candle_provider: Callable,
        result_checker: Callable
    ):
        self.bot_id = bot_id
        self.config = config
        self.strategy = strategy
        self.trade_executor = trade_executor
        self.candle_provider = candle_provider
        self.result_checker = result_checker
        
        # Manager de gales duales
        self.gale_manager = DualGaleManager(
            base_amount=config.trade_amount,
            max_gale=7,
            payout=0.87
        )
        
        # Stats y control
        self.stats = BotStats(bot_id=bot_id)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Tracking de trades pendientes
        self.pending_trades: Dict[str, Dict] = {}  # trade_id -> trade_info
        
    def start(self):
        """Inicia el bot"""
        if self.running:
            return
            
        self.running = True
        self.config.active = True
        self.stats.status = 'running'
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        print(f"🤖 Bot Gales Duales iniciado: {self.config.name}")
        
    def stop(self):
        """Detiene el bot"""
        self.running = False
        self.config.active = False
        self.stats.status = 'stopped'
        
        if self.thread:
            self.thread.join(timeout=5)
            
        print(f"🛑 Bot Gales Duales detenido: {self.config.name}")
        
    def _run_loop(self):
        """Loop principal del bot con detección de nueva vela"""
        last_candle_time = 0  # Timestamp de última vela analizada
        
        print(f"🚀 {self.config.name} - Loop iniciado, esperando velas...")
        
        while self.running:
            try:
                current_time = time.time()
                
                # 1. Verificar límites de trading
                if self._should_stop_trading():
                    self.stats.status = 'paused'
                    time.sleep(60)
                    continue
                
                # 2. Procesar resultados de trades pendientes
                self._process_pending_trades()
                
                # 3. Obtener velas actuales
                candles = self.candle_provider(
                    self.config.symbol,
                    self.config.timeframe
                )
                
                if candles and len(candles) >= self.strategy.min_candles:
                    current_candle_time = candles[-1].time
                    
                    # 4. Detectar nueva vela (ejecutar inmediatamente)
                    if current_candle_time != last_candle_time:
                        print(f"🕐 Nueva vela detectada: {current_candle_time} (última: {last_candle_time})")
                        self.stats.status = 'analyzing'
                        
                        signal = self.strategy.analyze(
                            self.config.symbol,
                            self.config.timeframe,
                            candles
                        )
                        
                        if signal:
                            print(f"🎯 Señal generada: {signal.direction} (confidence: {signal.confidence:.2f})")
                            self._handle_new_signal(signal)
                        else:
                            print(f"⚪ Sin señal en vela {current_candle_time}")
                        
                        last_candle_time = current_candle_time
                else:
                    if not candles:
                        print(f"⚠️ No se obtuvieron velas para {self.config.symbol}")
                
                self.stats.status = 'running'
                time.sleep(1)  # Check cada segundo para detección rápida
                
            except Exception as e:
                self.stats.status = 'error'
                self.stats.error_message = str(e)
                print(f"❌ Error en bot {self.config.name}: {e}")
                
                if not self.config.auto_restart:
                    self.stop()
                else:
                    time.sleep(30)
    
    def _handle_new_signal(self, signal: Signal):
        """Maneja una nueva señal detectada"""
        direction = signal.direction
        
        # Verificar si confidence cumple requisito
        if signal.confidence < 0.5:
            return
        
        # Intentar iniciar nueva secuencia
        trade_info = self.gale_manager.start_sequence(
            direction=direction,
            entry_price=signal.indicators.get('close', 0.0)
        )
        
        if trade_info:
            # Ejecutar trade
            self._execute_gale_trade(trade_info)
        # Si retorna None, significa que ya hay secuencia activa de ese tipo
    
    def _execute_gale_trade(self, trade_info: Dict):
        """Ejecuta un trade de gale"""
        try:
            result = self.trade_executor(
                symbol=self.config.symbol,
                direction=trade_info['direction'],
                amount=trade_info['amount'],
                duration=self.config.trade_duration
            )
            
            if result.get('success'):
                trade_id = result.get('trade_id', str(uuid.uuid4()))
                
                # Guardar en pending para verificar resultado
                self.pending_trades[trade_id] = {
                    **trade_info,
                    'trade_id': trade_id,
                    'start_time': int(time.time()),
                    'expiry_time': int(time.time()) + (self.config.trade_duration * 60),
                    'symbol': self.config.symbol
                }
                
                self.stats.total_trades += 1
                self.stats.trades_today += 1
                
                print(f"✅ Trade ejecutado: {trade_info['direction']} Gale {trade_info['gale_level']} - ${trade_info['amount']}")
                
        except Exception as e:
            print(f"❌ Error ejecutando trade: {e}")
    
    def _process_pending_trades(self):
        """Procesa resultados de trades pendientes"""
        current_time = int(time.time())
        completed_trades = []
        
        for trade_id, trade_info in list(self.pending_trades.items()):
            # Verificar si ya expiró (+ 30s de buffer)
            if current_time >= trade_info['expiry_time'] + 30:
                # Obtener resultado
                result = self._check_trade_result(trade_info)
                
                if result is not None:
                    # Procesar con gale manager
                    gale_result = self.gale_manager.process_result(
                        direction=trade_info['direction'],
                        won=result['won'],
                        close_price=result['close_price']
                    )
                    
                    # Actualizar stats
                    self._update_stats_from_gale_result(gale_result)
                    
                    # Si debe continuar con gale, ejecutar
                    if gale_result['action'] == 'continue_gale':
                        next_trade = {
                            'direction': gale_result['direction'],
                            'amount': gale_result['next_amount'],
                            'gale_level': gale_result['next_gale'],
                            'entry_price': result['close_price']
                        }
                        self._execute_gale_trade(next_trade)
                    
                    # Si ganó una secuencia, verificar si hay señal nueva en esa misma vela
                    elif gale_result['action'] == 'sequence_won':
                        print(f"🎉 Secuencia ganada - Verificando señal nueva en vela ganadora...")
                        
                        # Obtener velas actuales
                        candles = self.candle_provider(
                            self.config.symbol,
                            self.config.timeframe
                        )
                        
                        if candles and len(candles) >= self.strategy.min_candles:
                            # Analizar señal en vela actual
                            signal = self.strategy.analyze(
                                self.config.symbol,
                                self.config.timeframe,
                                candles
                            )
                            
                            if signal and signal.confidence >= 0.5:
                                print(f"✨ Nueva señal {signal.direction} detectada en vela ganadora - Iniciando nueva operación")
                                self._handle_new_signal(signal)
                    
                    completed_trades.append(trade_id)
        
        # Remover completados
        for trade_id in completed_trades:
            del self.pending_trades[trade_id]
    
    def _check_trade_result(self, trade_info: Dict) -> Optional[Dict]:
        """Verifica el resultado de un trade basándose en el COLOR de la vela"""
        try:
            # Obtener velas recientes
            candles = self.candle_provider(
                trade_info['symbol'],
                self.config.timeframe
            )
            
            if not candles or len(candles) < 2:
                return None
            
            # La vela de resultado es la última cerrada
            result_candle = candles[-1]
            close_price = result_candle.close
            open_price = result_candle.open
            direction = trade_info['direction']
            
            # Determinar si ganó basándose en COLOR de vela
            if direction == 'CALL':
                # COMPRA gana si vela es VERDE (close > open)
                won = close_price > open_price
            else:  # PUT
                # VENTA gana si vela es ROJA (close < open)
                won = close_price < open_price
            
            print(f"📊 Resultado: {direction} - Vela {'VERDE' if close_price > open_price else 'ROJA'} (O:{open_price:.5f} C:{close_price:.5f}) → {'✅ GANA' if won else '❌ PIERDE'}")
            
            return {
                'won': won,
                'close_price': close_price,
                'open_price': open_price,
                'result_candle': result_candle
            }
            
        except Exception as e:
            print(f"⚠️ Error verificando resultado: {e}")
            return None
    
    def _update_stats_from_gale_result(self, gale_result: Dict):
        """Actualiza estadísticas basado en resultado de gale"""
        action = gale_result['action']
        
        if action == 'sequence_won':
            self.stats.winning_trades += 1
            self.stats.total_profit += gale_result['profit']
            self.stats.daily_profit += gale_result['profit']
            
        elif action == 'sequence_lost':
            self.stats.losing_trades += 1
            self.stats.total_profit -= gale_result['loss']
            self.stats.daily_profit -= gale_result['loss']
        
        # Actualizar win rate
        total = self.stats.winning_trades + self.stats.losing_trades
        if total > 0:
            self.stats.win_rate = (self.stats.winning_trades / total) * 100
    
    def _should_stop_trading(self) -> bool:
        """Verifica si el bot debe dejar de operar"""
        if self.stats.daily_profit <= -self.config.max_daily_loss:
            print(f"⛔ Pérdida diaria máxima alcanzada: ${self.stats.daily_profit}")
            return True
            
        if self.stats.trades_today >= self.config.max_daily_trades:
            print(f"⛔ Límite de trades diarios alcanzado: {self.stats.trades_today}")
            return True
            
        return False
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas completas del bot y gales"""
        gale_stats = self.gale_manager.get_stats()
        
        return {
            'bot_stats': self.stats.to_dict(),
            'gale_stats': gale_stats,
            'pending_trades': len(self.pending_trades),
            'config': {
                'name': self.config.name,
                'symbol': self.config.symbol,
                'timeframe': self.config.timeframe,
                'base_amount': self.config.trade_amount
            }
        }
    
    def get_config(self) -> Dict:
        """Retorna configuración del bot"""
        return {
            'bot_id': self.bot_id,
            'name': self.config.name,
            'strategy_name': self.config.strategy_name,
            'symbol': self.config.symbol,
            'timeframe': self.config.timeframe,
            'trade_amount': self.config.trade_amount,
            'trade_duration': self.config.trade_duration,
            'max_daily_loss': self.config.max_daily_loss,
            'max_daily_trades': self.config.max_daily_trades,
            'active': self.config.active,
            'auto_restart': self.config.auto_restart,
            'use_dual_gale': True
        }
