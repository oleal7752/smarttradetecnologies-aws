"""
Estrategia de Probabilidades con Sistema de Gales (Martingala)
Basada en análisis estadístico de patrones de velas
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal


class ProbabilityGaleStrategy(Strategy):
    """
    Estrategia basada en probabilidades de patrones de velas:
    - Alcista: close > open
    - Bajista: close < open
    - Neutra: close == open
    - Martillo: patrón de vela con mecha inferior larga
    - Racha Alcista x3: 3 velas alcistas consecutivas
    
    Sistema de Gales (Martingala):
    - Gale 0 a Gale 7 (8 intentos máximo)
    - Cada gale duplica el monto: entrada_inicial * 2^gale
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'cantidad_velas': 100,
            'min_confidence': 0.55,
            'min_diff_percent': 5.0
        }
        if params:
            default_params.update(params)
            
        super().__init__('Probability + Gale System', default_params)
        self.min_candles = max(100, self.params['cantidad_velas'])
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula probabilidades de cada patrón"""
        cantidad_velas = min(self.params['cantidad_velas'], len(candles))
        
        alcistas = 0
        bajistas = 0
        neutras = 0
        martillos = 0
        racha_alcista = 0
        
        for i in range(cantidad_velas):
            idx = -(i + 1)
            
            # Verificar que el índice está dentro de rango
            if abs(idx) > len(candles):
                break
            
            c = candles[idx]
            
            is_alcista = 1 if c.close > c.open else 0
            is_bajista = 1 if c.close < c.open else 0
            is_neutra = 1 if c.close == c.open else 0
            
            alcistas += is_alcista
            bajistas += is_bajista
            neutras += is_neutra
            
            cuerpo = abs(c.close - c.open)
            rango_total = c.high - c.low
            mecha_inf = min(c.open, c.close) - c.low
            mecha_sup = c.high - max(c.open, c.close)
            
            if rango_total > 0:
                es_martillo = (cuerpo < rango_total * 0.3 and 
                              mecha_inf > cuerpo * 2 and 
                              mecha_sup < cuerpo)
                martillos += 1 if es_martillo else 0
            
            # Verificar que tenemos suficientes velas para calcular racha
            if i >= 2 and abs(idx - 2) <= len(candles):
                c1 = candles[idx]
                c2 = candles[idx - 1]
                c3 = candles[idx - 2]
                
                racha = (c1.close > c1.open and 
                        c2.close > c2.open and 
                        c3.close > c3.open)
                racha_alcista += 1 if racha else 0
        
        p_alcista = alcistas / cantidad_velas
        p_bajista = bajistas / cantidad_velas
        p_neutra = neutras / cantidad_velas
        p_martillo = martillos / cantidad_velas
        p_racha_alcista = racha_alcista / max(1, cantidad_velas - 2)
        
        return {
            'p_alcista': np.array([p_alcista]),
            'p_bajista': np.array([p_bajista]),
            'p_neutra': np.array([p_neutra]),
            'p_martillo': np.array([p_martillo]),
            'p_racha_alcista': np.array([p_racha_alcista])
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en la mayor probabilidad"""
        p_alcista = indicators['p_alcista'][0]
        p_bajista = indicators['p_bajista'][0]
        p_neutra = indicators['p_neutra'][0]
        p_martillo = indicators['p_martillo'][0]
        p_racha_alcista = indicators['p_racha_alcista'][0]
        
        probs = {
            'Alcista': p_alcista,
            'Bajista': p_bajista,
            'Neutra': p_neutra,
            'Martillo': p_martillo,
            'Racha Alcista x3': p_racha_alcista
        }
        
        max_name = max(probs, key=probs.get)
        max_val = probs[max_name]
        
        current_candle = candles[-1]
        is_alcista = current_candle.close > current_candle.open
        is_bajista = current_candle.close < current_candle.open
        
        min_conf = self.params['min_confidence']
        min_diff = self.params['min_diff_percent'] / 100
        
        if max_val < min_conf:
            return None
        
        # Verificar que haya al menos 2 valores diferentes antes de comparar
        sorted_probs = sorted(probs.values(), reverse=True)
        if len(sorted_probs) >= 2:
            segunda_mayor = sorted_probs[1]
            if (max_val - segunda_mayor) < min_diff:
                return None
        # Si solo hay 1 valor o todos son iguales, continuar sin verificar diferencia
        
        if max_name == "Alcista" and is_alcista:
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=current_candle.time,
                confidence=max_val,
                indicators={
                    'pattern': max_name,
                    'p_alcista': float(p_alcista),
                    'p_bajista': float(p_bajista),
                    'p_neutra': float(p_neutra),
                    'p_martillo': float(p_martillo),
                    'p_racha_alcista': float(p_racha_alcista),
                    'max_prob': float(max_val)
                },
                strategy_name=self.name
            )
            
        elif max_name == "Bajista" and is_bajista:
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=current_candle.time,
                confidence=max_val,
                indicators={
                    'pattern': max_name,
                    'p_alcista': float(p_alcista),
                    'p_bajista': float(p_bajista),
                    'p_neutra': float(p_neutra),
                    'p_martillo': float(p_martillo),
                    'p_racha_alcista': float(p_racha_alcista),
                    'max_prob': float(max_val)
                },
                strategy_name=self.name
            )
            
        return None


class GaleMoneyManager:
    """
    Gestor de Dinero con Sistema de Gales (Martingala)
    Gale 0 a Gale 7 (8 intentos totales)
    """
    
    def __init__(self, entrada_inicial: float = 2.0, max_gale: int = 7, payout: float = 0.8):
        self.entrada_inicial = entrada_inicial
        self.max_gale = max_gale
        self.payout = payout
        
        self.stats = {
            'total_ops': 0,
            'ganadas': 0,
            'perdidas': 0,
            'wins_by_gale': [0] * (max_gale + 1),
            'lost_gale_max': 0,
            'money_by_gale': [0.0] * (max_gale + 1),
            'money_lost_max': 0.0,
            'profit_total': 0.0,
            'loss_total': 0.0
        }
        
    def calculate_gale_amount(self, gale_index: int) -> float:
        """Calcula el monto para un gale específico (Martingala clásica)"""
        return self.entrada_inicial * (2 ** gale_index)
    
    def calculate_total_investment(self, gale_index: int) -> float:
        """Calcula la inversión total hasta un gale específico"""
        total = 0.0
        for i in range(gale_index + 1):
            total += self.calculate_gale_amount(i)
        return total
    
    def process_trade_sequence(self, signal_direction: str, future_candles: List[Candle]) -> Dict:
        """
        Procesa una secuencia de trades con gales
        
        Args:
            signal_direction: 'CALL' o 'PUT'
            future_candles: Velas futuras para validar resultados
            
        Returns:
            Dict con resultado final del trade con gales
        """
        self.stats['total_ops'] += 1
        
        gano = False
        gale_ganador = -1
        monto_total_invertido = 0.0
        profit_final = 0.0
        
        for g in range(self.max_gale + 1):
            if g >= len(future_candles):
                break
                
            monto_gale = self.calculate_gale_amount(g)
            monto_total_invertido += monto_gale
            
            candle_resultado = future_candles[g]
            
            if signal_direction == 'CALL':
                win = candle_resultado.close > candle_resultado.open
            else:
                win = candle_resultado.close < candle_resultado.open
            
            if win:
                profit = monto_gale * self.payout
                profit_final = profit - (monto_total_invertido - monto_gale)
                
                self.stats['ganadas'] += 1
                self.stats['wins_by_gale'][g] += 1
                self.stats['money_by_gale'][g] += profit
                self.stats['profit_total'] += profit_final
                
                gano = True
                gale_ganador = g
                break
        
        if not gano:
            self.stats['perdidas'] += 1
            self.stats['lost_gale_max'] += 1
            self.stats['loss_total'] += monto_total_invertido
            self.stats['money_lost_max'] += monto_total_invertido
            profit_final = -monto_total_invertido
        
        return {
            'success': gano,
            'gale_ganador': gale_ganador,
            'monto_invertido': monto_total_invertido,
            'profit': profit_final,
            'total_ops': self.stats['total_ops'],
            'win_rate': (self.stats['ganadas'] / self.stats['total_ops'] * 100) if self.stats['total_ops'] > 0 else 0
        }
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas completas del sistema de gales"""
        return {
            'total_operaciones': self.stats['total_ops'],
            'ganadas': self.stats['ganadas'],
            'perdidas': self.stats['perdidas'],
            'win_rate': (self.stats['ganadas'] / self.stats['total_ops'] * 100) if self.stats['total_ops'] > 0 else 0,
            'wins_por_gale': self.stats['wins_by_gale'],
            'dinero_por_gale': self.stats['money_by_gale'],
            'perdidas_gale_max': self.stats['lost_gale_max'],
            'dinero_perdido_max': self.stats['money_lost_max'],
            'profit_total': self.stats['profit_total'],
            'loss_total': self.stats['loss_total'],
            'net_profit': self.stats['profit_total'] - self.stats['loss_total']
        }
