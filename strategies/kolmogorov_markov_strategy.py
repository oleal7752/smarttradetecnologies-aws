"""
Estrategia de Kolmogorov Probabilístico - Cadenas de Markov
Basada en teoría de procesos estocásticos de Kolmogorov
Analiza transiciones entre estados de velas para predecir movimientos
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from collections import defaultdict
from strategy_engine import Strategy, Candle, Signal


class KolmogorovMarkovStrategy(Strategy):
    """
    Estrategia basada en Cadenas de Markov (Teoría de Kolmogorov)
    
    Estados posibles:
    - U (Up): Vela alcista (close > open)
    - D (Down): Vela bajista (close < open)
    - N (Neutral): Vela neutra (close == open)
    
    Calcula matriz de probabilidades de transición:
    P(próximo estado | secuencia de estados anteriores)
    
    Ejemplo:
    Si vemos secuencia "UUD" → ¿cuál es P(U)? ¿P(D)?
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'sequence_length': 3,
            'min_samples': 20,
            'min_confidence': 0.65,
            'use_body_size': True,
            'min_body_threshold': 0.0001
        }
        if params:
            default_params.update(params)
            
        super().__init__('Kolmogorov-Markov Chain', default_params)
        self.min_candles = max(100, self.params['sequence_length'] * 10)
        
    def _get_candle_state(self, candle: Candle) -> str:
        """Determina el estado de una vela: U (Up), D (Down), N (Neutral)"""
        body = candle.close - candle.open
        
        if self.params['use_body_size']:
            threshold = self.params['min_body_threshold']
            if abs(body) < threshold:
                return 'N'
        
        if candle.close > candle.open:
            return 'U'
        elif candle.close < candle.open:
            return 'D'
        else:
            return 'N'
    
    def _build_transition_matrix(self, candles: List[Candle]) -> Dict[str, Dict[str, float]]:
        """
        Construye matriz de probabilidades de transición
        
        Returns:
            Dict[secuencia, Dict[próximo_estado, probabilidad]]
        """
        seq_len = self.params['sequence_length']
        transitions = defaultdict(lambda: defaultdict(int))
        
        for i in range(len(candles) - seq_len):
            sequence = ''.join([self._get_candle_state(candles[i + j]) 
                               for j in range(seq_len)])
            
            next_state = self._get_candle_state(candles[i + seq_len])
            
            transitions[sequence][next_state] += 1
        
        probabilities = {}
        for sequence, next_states in transitions.items():
            total = sum(next_states.values())
            if total >= self.params['min_samples']:
                probabilities[sequence] = {
                    state: count / total 
                    for state, count in next_states.items()
                }
        
        return probabilities
    
    def _calculate_entropy(self, probs: Dict[str, float]) -> float:
        """
        Calcula entropía de Shannon (medida de incertidumbre)
        Menor entropía = mayor confianza en la predicción
        """
        entropy = 0.0
        for p in probs.values():
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy
    
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula matriz de transición y estadísticas"""
        transition_matrix = self._build_transition_matrix(candles)
        
        seq_len = self.params['sequence_length']
        current_sequence = ''.join([self._get_candle_state(candles[-(i+1)]) 
                                    for i in range(seq_len-1, -1, -1)])
        
        probs = transition_matrix.get(current_sequence, {})
        
        p_up = probs.get('U', 0.0)
        p_down = probs.get('D', 0.0)
        p_neutral = probs.get('N', 0.0)
        
        entropy = self._calculate_entropy(probs) if probs else 999
        
        total_patterns = len(transition_matrix)
        
        return {
            'current_sequence': np.array([current_sequence], dtype=object),
            'p_up': np.array([p_up]),
            'p_down': np.array([p_down]),
            'p_neutral': np.array([p_neutral]),
            'entropy': np.array([entropy]),
            'total_patterns': np.array([total_patterns]),
            'transition_matrix': transition_matrix
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en probabilidades de transición de Markov"""
        p_up = indicators['p_up'][0]
        p_down = indicators['p_down'][0]
        p_neutral = indicators['p_neutral'][0]
        entropy = indicators['entropy'][0]
        current_sequence = str(indicators['current_sequence'][0])
        
        if p_up == 0 and p_down == 0:
            return None
        
        min_conf = self.params['min_confidence']
        
        max_prob = max(p_up, p_down, p_neutral)
        
        if max_prob < min_conf:
            return None
        
        if entropy > 1.5:
            return None
        
        current_candle = candles[-1]
        
        if p_up > p_down and p_up >= min_conf:
            confidence = p_up
            
            if p_up - p_down < 0.15:
                return None
            
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=current_candle.time,
                confidence=confidence,
                indicators={
                    'sequence': current_sequence,
                    'p_up': float(p_up),
                    'p_down': float(p_down),
                    'p_neutral': float(p_neutral),
                    'entropy': float(entropy),
                    'method': 'Markov Chain',
                    'confidence_margin': float(p_up - p_down)
                },
                strategy_name=self.name
            )
            
        elif p_down > p_up and p_down >= min_conf:
            confidence = p_down
            
            if p_down - p_up < 0.15:
                return None
            
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=current_candle.time,
                confidence=confidence,
                indicators={
                    'sequence': current_sequence,
                    'p_up': float(p_up),
                    'p_down': float(p_down),
                    'p_neutral': float(p_neutral),
                    'entropy': float(entropy),
                    'method': 'Markov Chain',
                    'confidence_margin': float(p_down - p_up)
                },
                strategy_name=self.name
            )
        
        return None


class KolmogorovComplexityStrategy(Strategy):
    """
    Estrategia basada en Complejidad de Kolmogorov
    
    Mide la complejidad/aleatoriedad de secuencias de precios
    - Alta complejidad → mercado aleatorio → evitar trading
    - Baja complejidad → patrones detectables → trading
    
    Usa LZ77 compression ratio como proxy de complejidad
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'window_size': 50,
            'complexity_threshold': 0.7,
            'min_confidence': 0.65,
            'momentum_periods': 3
        }
        if params:
            default_params.update(params)
            
        super().__init__('Kolmogorov Complexity', default_params)
        self.min_candles = max(100, self.params['window_size'] * 2)
    
    def _lz_complexity(self, sequence: str) -> float:
        """
        Calcula complejidad Lempel-Ziv (proxy de complejidad de Kolmogorov)
        Retorna valor entre 0 y 1
        """
        if not sequence:
            return 0.0
        
        n = len(sequence)
        i = 0
        complexity = 1
        
        while i < n - 1:
            j = i + 1
            while j < n:
                substring = sequence[i:j]
                if substring in sequence[:i]:
                    j += 1
                else:
                    break
            complexity += 1
            i = j
        
        max_complexity = n / np.log2(n) if n > 1 else 1
        normalized = complexity / max_complexity if max_complexity > 0 else 0
        
        return min(1.0, normalized)
    
    def _encode_price_sequence(self, candles: List[Candle]) -> str:
        """Codifica secuencia de precios como string binario"""
        sequence = ''
        for i in range(1, len(candles)):
            if candles[i].close > candles[i-1].close:
                sequence += '1'
            elif candles[i].close < candles[i-1].close:
                sequence += '0'
            else:
                sequence += 'X'
        return sequence
    
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula complejidad y momentum"""
        window = self.params['window_size']
        recent_candles = candles[-window:]
        
        price_sequence = self._encode_price_sequence(recent_candles)
        complexity = self._lz_complexity(price_sequence)
        
        momentum_periods = self.params['momentum_periods']
        closes = np.array([c.close for c in candles[-momentum_periods-1:]])
        momentum = (closes[-1] - closes[0]) / closes[0] if closes[0] != 0 else 0
        
        recent_trend = sum([1 if candles[-(i+1)].close > candles[-(i+2)].close else -1 
                           for i in range(min(5, len(candles)-1))])
        
        return {
            'complexity': np.array([complexity]),
            'momentum': np.array([momentum]),
            'recent_trend': np.array([recent_trend]),
            'price_sequence': np.array([price_sequence], dtype=object)
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal cuando complejidad es baja (patrones detectables)"""
        complexity = indicators['complexity'][0]
        momentum = indicators['momentum'][0]
        recent_trend = indicators['recent_trend'][0]
        
        threshold = self.params['complexity_threshold']
        
        if complexity > threshold:
            return None
        
        predictability = 1.0 - complexity
        
        if predictability < self.params['min_confidence']:
            return None
        
        current_candle = candles[-1]
        
        if momentum > 0 and recent_trend > 1:
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=current_candle.time,
                confidence=predictability,
                indicators={
                    'complexity': float(complexity),
                    'predictability': float(predictability),
                    'momentum': float(momentum),
                    'recent_trend': int(recent_trend),
                    'method': 'Kolmogorov Complexity'
                },
                strategy_name=self.name
            )
            
        elif momentum < 0 and recent_trend < -1:
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=current_candle.time,
                confidence=predictability,
                indicators={
                    'complexity': float(complexity),
                    'predictability': float(predictability),
                    'momentum': float(momentum),
                    'recent_trend': int(recent_trend),
                    'method': 'Kolmogorov Complexity'
                },
                strategy_name=self.name
            )
        
        return None
