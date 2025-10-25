"""
Sistema de Gales Duales - STC Trading System
Gestiona secuencias de CALL y PUT independientes con sistema de martingala
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import time


@dataclass
class GaleSequence:
    """Secuencia de gales activa (CALL o PUT)"""
    direction: str  # 'CALL' o 'PUT'
    current_gale: int  # 0-7
    entry_price: float
    start_time: int
    total_invested: float
    trades: List[Dict]  # Historial de trades en esta secuencia
    active: bool = True
    
    GALE_LADDER_87 = [5.0, 10.75, 23.1, 49.65, 106.72, 229.39, 493.06, 1059.81]
    
    def get_next_amount(self, base_amount: float, payout: float = 0.87) -> float:
        """Calcula monto del próximo gale usando tabla payout-aware"""
        next_gale = self.current_gale + 1
        if next_gale >= len(self.GALE_LADDER_87):
            return base_amount * (2 ** next_gale)
        return self.GALE_LADDER_87[next_gale] * (base_amount / 5.0)
    
    def get_current_amount(self, base_amount: float, payout: float = 0.87) -> float:
        """Calcula monto del gale actual usando tabla payout-aware"""
        if self.current_gale >= len(self.GALE_LADDER_87):
            return base_amount * (2 ** self.current_gale)
        return self.GALE_LADDER_87[self.current_gale] * (base_amount / 5.0)
    
    def can_continue(self, max_gale: int = 7) -> bool:
        """Verifica si puede continuar con más gales"""
        return self.active and self.current_gale < max_gale


class DualGaleManager:
    """
    Gestor de Gales Duales - Maneja CALL y PUT independientemente
    
    Características:
    - Secuencias paralelas de CALL y PUT
    - Cada una con su propio contador de gales (0-7)
    - Nuevas señales no cancelan gales activos
    - Tracking separado de profit/loss
    """
    
    def __init__(self, base_amount: float = 5.0, max_gale: int = 7, payout: float = 0.87):
        self.base_amount = base_amount
        self.max_gale = max_gale
        self.payout = payout
        
        # Secuencias activas
        self.call_sequence: Optional[GaleSequence] = None
        self.put_sequence: Optional[GaleSequence] = None
        
        # Estadísticas globales
        self.stats = {
            'total_sequences': 0,
            'won_sequences': 0,
            'lost_sequences': 0,
            'total_profit': 0.0,
            'total_invested': 0.0,
            'wins_by_gale': {'CALL': [0]*8, 'PUT': [0]*8},
            'losses_at_max_gale': {'CALL': 0, 'PUT': 0},
            'active_trades': 0
        }
        
    def start_sequence(self, direction: str, entry_price: float, allow_override: bool = True) -> Optional[Dict]:
        """
        Inicia una nueva secuencia de gales
        
        Args:
            allow_override: Si True, permite iniciar nueva secuencia aunque haya una activa (solo en Gale 0)
        
        Returns:
            Dict con información del trade a ejecutar, o None si hay secuencia activa de gale > 0
        """
        if direction == 'CALL':
            if self.call_sequence and self.call_sequence.active:
                # Solo bloquear si está en Gale > 0 (en recuperación)
                if self.call_sequence.current_gale > 0:
                    print(f"⚠️ CALL en recuperación (Gale {self.call_sequence.current_gale}) - bloqueando nueva entrada")
                    return None
                # Si está en Gale 0 y allow_override=True, permitir nueva entrada
                elif not allow_override:
                    print(f"⚠️ Ya hay secuencia CALL activa en Gale {self.call_sequence.current_gale}")
                    return None
                else:
                    print(f"✨ Reemplazando secuencia CALL Gale 0 con nueva entrada")
                
            self.call_sequence = GaleSequence(
                direction='CALL',
                current_gale=0,
                entry_price=entry_price,
                start_time=int(time.time()),
                total_invested=0.0,
                trades=[]
            )
            sequence = self.call_sequence
            
        elif direction == 'PUT':
            if self.put_sequence and self.put_sequence.active:
                # Solo bloquear si está en Gale > 0 (en recuperación)
                if self.put_sequence.current_gale > 0:
                    print(f"⚠️ PUT en recuperación (Gale {self.put_sequence.current_gale}) - bloqueando nueva entrada")
                    return None
                # Si está en Gale 0 y allow_override=True, permitir nueva entrada
                elif not allow_override:
                    print(f"⚠️ Ya hay secuencia PUT activa en Gale {self.put_sequence.current_gale}")
                    return None
                else:
                    print(f"✨ Reemplazando secuencia PUT Gale 0 con nueva entrada")
                
            self.put_sequence = GaleSequence(
                direction='PUT',
                current_gale=0,
                entry_price=entry_price,
                start_time=int(time.time()),
                total_invested=0.0,
                trades=[]
            )
            sequence = self.put_sequence
        else:
            return None
        
        amount = self.base_amount
        sequence.total_invested = amount
        self.stats['total_sequences'] += 1
        self.stats['active_trades'] += 1
        
        trade_info = {
            'direction': direction,
            'amount': amount,
            'gale_level': 0,
            'sequence_id': f"{direction}_{sequence.start_time}",
            'entry_price': entry_price
        }
        
        print(f"🎯 Nueva secuencia {direction} iniciada - Gale 0: ${amount}")
        return trade_info
    
    def process_result(self, direction: str, won: bool, close_price: float) -> Dict:
        """
        Procesa el resultado de un trade y determina próxima acción
        
        Args:
            direction: 'CALL' o 'PUT'
            won: True si ganó, False si perdió
            close_price: Precio de cierre de la vela
            
        Returns:
            Dict con acción a tomar: 'continue_gale', 'sequence_won', 'sequence_lost', 'next_trade'
        """
        sequence = self.call_sequence if direction == 'CALL' else self.put_sequence
        
        if not sequence or not sequence.active:
            return {'action': 'no_active_sequence'}
        
        # Registrar resultado
        current_amount = sequence.get_current_amount(self.base_amount, self.payout)
        
        trade_record = {
            'gale_level': sequence.current_gale,
            'amount': current_amount,
            'won': won,
            'close_price': close_price,
            'timestamp': int(time.time())
        }
        sequence.trades.append(trade_record)
        
        if won:
            # ✅ GANÓ - Secuencia terminada
            profit = current_amount * self.payout
            net_profit = profit - sequence.total_invested
            
            sequence.active = False
            self.stats['won_sequences'] += 1
            self.stats['total_profit'] += net_profit
            self.stats['total_invested'] += sequence.total_invested
            self.stats['wins_by_gale'][direction][sequence.current_gale] += 1
            self.stats['active_trades'] -= 1
            
            print(f"✅ {direction} ganó en Gale {sequence.current_gale}!")
            print(f"   💰 Profit neto: ${net_profit:.2f} (invertido: ${sequence.total_invested:.2f})")
            
            return {
                'action': 'sequence_won',
                'direction': direction,
                'gale_level': sequence.current_gale,
                'profit': net_profit,
                'total_invested': sequence.total_invested,
                'trades': sequence.trades
            }
        else:
            # ❌ PERDIÓ - Continuar con siguiente gale o terminar
            if sequence.can_continue(self.max_gale):
                # Continuar con siguiente gale
                sequence.current_gale += 1
                next_amount = sequence.get_current_amount(self.base_amount, self.payout)
                sequence.total_invested += next_amount
                
                print(f"📉 {direction} perdió en Gale {sequence.current_gale - 1}")
                print(f"   ➡️ Siguiente: Gale {sequence.current_gale} con ${next_amount}")
                
                return {
                    'action': 'continue_gale',
                    'direction': direction,
                    'next_gale': sequence.current_gale,
                    'next_amount': next_amount,
                    'total_invested': sequence.total_invested
                }
            else:
                # Llegó a Gale máximo y perdió
                sequence.active = False
                self.stats['lost_sequences'] += 1
                self.stats['total_profit'] -= sequence.total_invested
                self.stats['total_invested'] += sequence.total_invested
                self.stats['losses_at_max_gale'][direction] += 1
                self.stats['active_trades'] -= 1
                
                print(f"❌ {direction} perdió secuencia completa (Gale {self.max_gale})")
                print(f"   💸 Pérdida total: ${sequence.total_invested:.2f}")
                
                return {
                    'action': 'sequence_lost',
                    'direction': direction,
                    'loss': sequence.total_invested,
                    'trades': sequence.trades
                }
    
    def get_active_sequences(self) -> List[Dict]:
        """Retorna información de secuencias activas"""
        active = []
        
        if self.call_sequence and self.call_sequence.active:
            active.append({
                'direction': 'CALL',
                'gale_level': self.call_sequence.current_gale,
                'total_invested': self.call_sequence.total_invested,
                'next_amount': self.call_sequence.get_current_amount(self.base_amount, self.payout),
                'trades_count': len(self.call_sequence.trades)
            })
            
        if self.put_sequence and self.put_sequence.active:
            active.append({
                'direction': 'PUT',
                'gale_level': self.put_sequence.current_gale,
                'total_invested': self.put_sequence.total_invested,
                'next_amount': self.put_sequence.get_current_amount(self.base_amount, self.payout),
                'trades_count': len(self.put_sequence.trades)
            })
            
        return active
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas completas"""
        win_rate = 0.0
        if self.stats['total_sequences'] > 0:
            win_rate = (self.stats['won_sequences'] / self.stats['total_sequences']) * 100
        
        return {
            **self.stats,
            'win_rate': win_rate,
            'active_sequences': self.get_active_sequences(),
            'call_active': self.call_sequence is not None and self.call_sequence.active,
            'put_active': self.put_sequence is not None and self.put_sequence.active
        }
    
    def reset(self):
        """Resetea el manager (para testing)"""
        self.call_sequence = None
        self.put_sequence = None
        self.stats = {
            'total_sequences': 0,
            'won_sequences': 0,
            'lost_sequences': 0,
            'total_profit': 0.0,
            'total_invested': 0.0,
            'wins_by_gale': {'CALL': [0]*8, 'PUT': [0]*8},
            'losses_at_max_gale': {'CALL': 0, 'PUT': 0},
            'active_trades': 0
        }
