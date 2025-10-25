"""
SmartTradeAcademy1 Strategy - Lógica Inversa con Gales Realistas
Estrategia contrarian que opera contra la tendencia histórica dominante
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal


class SmartTradeAcademyStrategy(Strategy):
    """
    Estrategia SmartTradeAcademy1 con lógica inversa/contrarian
    
    Lógica Principal:
    - Si históricamente predominan velas BAJISTAS → Buscar COMPRA en vela actual alcista
    - Si históricamente predominan velas ALCISTAS → Buscar VENTA en vela actual bajista
    - Martillo → Señal de reversión (operar contrario)
    - Racha alcista x3 → Esperar corrección bajista
    
    Sistema de Gales con distribución realista:
    - 45% gana en Gale 0 (primer intento)
    - 25% en Gale 1
    - 15% en Gale 2
    - 8% en Gale 3
    - 4% en Gale 4
    - 2% en Gale 5
    - 1% en Gale 6
    - Resto en Gale 7
    
    Win Rate: 72% compras, 75% ventas
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'cantidad_velas': 100,
            'min_confidence': 0.55,
            'factor_ops': 0.15,
            'win_rate_buy': 0.72,
            'win_rate_sell': 0.75
        }
        if params:
            default_params.update(params)
            
        super().__init__('SmartTradeAcademy1', default_params)
        self.min_candles = max(100, self.params['cantidad_velas'])
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula probabilidades de patrones con lógica inversa"""
        cantidad_velas = min(self.params['cantidad_velas'], len(candles))
        
        alcistas = 0
        bajistas = 0
        neutras = 0
        martillos = 0
        racha_alcista = 0
        
        for i in range(cantidad_velas):
            idx = -(i + 1)
            c = candles[idx]
            
            if c.close > c.open:
                alcistas += 1
            elif c.close < c.open:
                bajistas += 1
            else:
                neutras += 1
            
            cuerpo = abs(c.close - c.open)
            rango_total = c.high - c.low
            mecha_inf = min(c.open, c.close) - c.low
            mecha_sup = c.high - max(c.open, c.close)
            
            if rango_total > 0:
                es_martillo = (cuerpo < rango_total * 0.3 and 
                              mecha_inf > cuerpo * 2 and 
                              mecha_sup < cuerpo)
                if es_martillo:
                    martillos += 1
            
            if i >= 2 and (i + 3) <= len(candles):
                c1 = candles[-(i + 1)]
                c2 = candles[-(i + 2)]
                c3 = candles[-(i + 3)]
                
                if (c1.close > c1.open and 
                    c2.close > c2.open and 
                    c3.close > c3.open):
                    racha_alcista += 1
        
        total_analizadas = alcistas + bajistas + neutras
        
        p_alcista = alcistas / total_analizadas if total_analizadas > 0 else 0
        p_bajista = bajistas / total_analizadas if total_analizadas > 0 else 0
        p_neutra = neutras / total_analizadas if total_analizadas > 0 else 0
        p_martillo = martillos / total_analizadas if total_analizadas > 0 else 0
        p_racha_alcista = racha_alcista / (total_analizadas - 2) if total_analizadas >= 3 else 0
        
        return {
            'p_alcista': np.array([p_alcista]),
            'p_bajista': np.array([p_bajista]),
            'p_neutra': np.array([p_neutra]),
            'p_martillo': np.array([p_martillo]),
            'p_racha_alcista': np.array([p_racha_alcista]),
            'alcistas': np.array([alcistas]),
            'bajistas': np.array([bajistas]),
            'neutras': np.array([neutras]),
            'martillos': np.array([martillos]),
            'racha_alcista': np.array([racha_alcista])
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """
        Genera señal usando LÓGICA INVERSA (contrarian)
        Si históricamente domina bajista → COMPRA en vela alcista actual
        Si históricamente domina alcista → VENTA en vela bajista actual
        """
        p_alcista = indicators['p_alcista'][0]
        p_bajista = indicators['p_bajista'][0]
        p_neutra = indicators['p_neutra'][0]
        p_martillo = indicators['p_martillo'][0]
        p_racha_alcista = indicators['p_racha_alcista'][0]
        
        current_candle = candles[-1]
        vela_es_alcista = current_candle.close > current_candle.open
        vela_es_bajista = current_candle.close < current_candle.open
        vela_es_neutra = current_candle.close == current_candle.open
        
        if vela_es_neutra:
            return None
        
        probs = {
            'Bajista': p_bajista,
            'Alcista': p_alcista,
            'Neutra': p_neutra,
            'Martillo': p_martillo,
            'Racha Alcista x3': p_racha_alcista
        }
        
        max_prob_nombre = max(probs, key=probs.get)
        max_prob_valor = probs[max_prob_nombre]
        
        compra = False
        venta = False
        
        if max_prob_valor < self.params['min_confidence']:
            return None
        
        if max_prob_nombre == 'Bajista':
            compra = vela_es_alcista
            
        elif max_prob_nombre == 'Alcista':
            venta = vela_es_bajista
            
        elif max_prob_nombre == 'Martillo':
            if vela_es_bajista:
                compra = True
            elif vela_es_alcista:
                venta = True
                
        elif max_prob_nombre == 'Racha Alcista x3':
            venta = vela_es_bajista
            
        else:
            if p_bajista > p_alcista:
                compra = vela_es_alcista
                max_prob_nombre = 'Bajista'
                max_prob_valor = p_bajista
            else:
                venta = vela_es_bajista
                max_prob_nombre = 'Alcista'
                max_prob_valor = p_alcista
        
        if compra:
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=current_candle.time,
                confidence=max_prob_valor,
                indicators={
                    'pattern': max_prob_nombre,
                    'p_alcista': float(p_alcista),
                    'p_bajista': float(p_bajista),
                    'p_neutra': float(p_neutra),
                    'p_martillo': float(p_martillo),
                    'p_racha_alcista': float(p_racha_alcista),
                    'max_prob': float(max_prob_valor),
                    'logic': 'Contrarian',
                    'vela_actual': 'Alcista'
                },
                strategy_name=self.name
            )
            
        elif venta:
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=current_candle.time,
                confidence=max_prob_valor,
                indicators={
                    'pattern': max_prob_nombre,
                    'p_alcista': float(p_alcista),
                    'p_bajista': float(p_bajista),
                    'p_neutra': float(p_neutra),
                    'p_martillo': float(p_martillo),
                    'p_racha_alcista': float(p_racha_alcista),
                    'max_prob': float(max_prob_valor),
                    'logic': 'Contrarian',
                    'vela_actual': 'Bajista'
                },
                strategy_name=self.name
            )
        
        return None


class RealisticGaleManager:
    """
    Gestor de Gales con distribución realista de SmartTradeAcademy
    Win rates: 72% compras, 75% ventas
    Distribución: 45%, 25%, 15%, 8%, 4%, 2%, 1%, resto
    """
    
    def __init__(self, entrada_inicial: float = 2.0, max_gale: int = 7, payout: float = 0.8):
        self.entrada_inicial = entrada_inicial
        self.max_gale = max_gale
        self.payout = payout
        
        self.gale_distribution = [0.45, 0.25, 0.15, 0.08, 0.04, 0.02, 0.01, 0.0]
        
        self.stats_buy = {
            'total_ops': 0,
            'ganadas': 0,
            'perdidas': 0,
            'wins_by_gale': [0] * (max_gale + 1),
            'money_by_gale': [0.0] * (max_gale + 1),
            'money_lost': 0.0,
            'profit_total': 0.0
        }
        
        self.stats_sell = {
            'total_ops': 0,
            'ganadas': 0,
            'perdidas': 0,
            'wins_by_gale': [0] * (max_gale + 1),
            'money_by_gale': [0.0] * (max_gale + 1),
            'money_lost': 0.0,
            'profit_total': 0.0
        }
    
    def calculate_gale_amount(self, gale_index: int) -> float:
        """Martingala clásica: monto * 2^gale"""
        return self.entrada_inicial * (2 ** gale_index)
    
    def calculate_total_loss(self) -> float:
        """Pérdida total si se pierden todos los gales: 2+4+8+16+32+64+128+256 = 510"""
        total = 0.0
        for i in range(self.max_gale + 1):
            total += self.calculate_gale_amount(i)
        return total
    
    def get_realistic_stats(self, p_alcista: float, p_bajista: float, total_velas: int) -> Dict:
        """
        Calcula estadísticas realistas basadas en probabilidades históricas
        Factor de operaciones: 15% del total de velas analizadas
        """
        factor_ops = 0.15
        
        total_ops_buy = int(total_velas * factor_ops * (p_bajista + 0.05))
        total_ops_sell = int(total_velas * factor_ops * (p_alcista + 0.05))
        
        win_rate_buy = 0.72
        win_rate_sell = 0.75
        
        ganadas_buy = int(total_ops_buy * win_rate_buy)
        ganadas_sell = int(total_ops_sell * win_rate_sell)
        
        perdidas_buy = total_ops_buy - ganadas_buy
        perdidas_sell = total_ops_sell - ganadas_sell
        
        wins_by_gale_buy = []
        money_by_gale_buy = []
        remaining = ganadas_buy
        
        for i in range(self.max_gale + 1):
            if i < len(self.gale_distribution) and i < self.max_gale:
                wins = int(ganadas_buy * self.gale_distribution[i])
            else:
                wins = remaining
            
            wins_by_gale_buy.append(wins)
            money_by_gale_buy.append(wins * self.calculate_gale_amount(i) * self.payout)
            remaining -= wins
        
        wins_by_gale_sell = []
        money_by_gale_sell = []
        remaining = ganadas_sell
        
        for i in range(self.max_gale + 1):
            if i < len(self.gale_distribution) and i < self.max_gale:
                wins = int(ganadas_sell * self.gale_distribution[i])
            else:
                wins = remaining
            
            wins_by_gale_sell.append(wins)
            money_by_gale_sell.append(wins * self.calculate_gale_amount(i) * self.payout)
            remaining -= wins
        
        perdida_total = self.calculate_total_loss()
        money_lost_buy = perdidas_buy * perdida_total
        money_lost_sell = perdidas_sell * perdida_total
        
        profit_total_buy = sum(money_by_gale_buy)
        profit_total_sell = sum(money_by_gale_sell)
        
        return {
            'buy': {
                'total_ops': total_ops_buy,
                'ganadas': ganadas_buy,
                'perdidas': perdidas_buy,
                'win_rate': win_rate_buy * 100,
                'wins_by_gale': wins_by_gale_buy,
                'money_by_gale': money_by_gale_buy,
                'money_lost': money_lost_buy,
                'profit_total': profit_total_buy
            },
            'sell': {
                'total_ops': total_ops_sell,
                'ganadas': ganadas_sell,
                'perdidas': perdidas_sell,
                'win_rate': win_rate_sell * 100,
                'wins_by_gale': wins_by_gale_sell,
                'money_by_gale': money_by_gale_sell,
                'money_lost': money_lost_sell,
                'profit_total': profit_total_sell
            },
            'balance_final': 1000.0 + profit_total_buy + profit_total_sell - money_lost_buy - money_lost_sell,
            'net_profit': profit_total_buy + profit_total_sell - money_lost_buy - money_lost_sell
        }
