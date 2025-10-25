"""
Tablero Binarias Logic - Indicador de Señales
Análisis de probabilidades siguiendo patrón dominante
Basada en la estrategia de oleal7752 (PineScript)
"""

from strategy_engine import Strategy, Candle, Signal
from typing import List, Dict, Optional
import numpy as np


class TableroBinariasStrategy(Strategy):
    """
    Indicador de señales basado en análisis de probabilidades
    Lógica de seguimiento: si patrón dominante es Alcista → COMPRA en vela alcista
    """
    
    def __init__(self):
        super().__init__(
            name="Tablero Binarias",
            params={'cantidad_velas': 100}
        )
        self.cantidad_velas = 100
        self.min_candles = 10
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula indicadores: probabilidades de patrones"""
        analysis = self._analyze_patterns(candles)
        
        # Convertir a arrays de numpy (requerido por interfaz)
        return {
            'p_alcista': np.array([analysis['p_alcista']]),
            'p_bajista': np.array([analysis['p_bajista']]),
            'p_neutra': np.array([analysis['p_neutra']]),
            'p_martillo': np.array([analysis['p_martillo']]),
            'p_racha_alcista': np.array([analysis['p_racha_alcista']])
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en probabilidades e indicadores"""
        if len(candles) < self.min_candles:
            return None
        
        # Extraer indicadores (5 patrones)
        p_alcista = float(indicators['p_alcista'][-1]) if len(indicators['p_alcista']) > 0 else 0
        p_bajista = float(indicators['p_bajista'][-1]) if len(indicators['p_bajista']) > 0 else 0
        p_neutra = float(indicators['p_neutra'][-1]) if len(indicators['p_neutra']) > 0 else 0
        p_martillo = float(indicators['p_martillo'][-1]) if len(indicators['p_martillo']) > 0 else 0
        p_racha_alcista = float(indicators['p_racha_alcista'][-1]) if len(indicators['p_racha_alcista']) > 0 else 0
        
        analysis = {
            'p_alcista': p_alcista,
            'p_bajista': p_bajista,
            'p_neutra': p_neutra,
            'p_martillo': p_martillo,
            'p_racha_alcista': p_racha_alcista
        }
        
        # Generar señal usando lógica TradingView (5 patrones)
        signal = self._generate_signal_logic(candles, analysis)
        
        return signal
    
    def _analyze_patterns(self, candles: List[Candle]) -> dict:
        """Analiza patrones en las últimas N velas"""
        total_velas = min(self.cantidad_velas, len(candles))
        
        alcistas = 0
        bajistas = 0
        neutras = 0
        martillos = 0
        racha_alcista = 0
        
        # Analizar cada vela
        for i in range(1, total_velas + 1):
            idx = len(candles) - i
            if idx < 0:
                break
                
            candle = candles[idx]
            c = candle.close
            o = candle.open
            h = candle.high
            l = candle.low
            
            # Contar tipos de velas
            if c > o:
                alcistas += 1
            elif c < o:
                bajistas += 1
            else:
                neutras += 1
            
            # Detectar martillos
            cuerpo = abs(c - o)
            mecha_inf = min(o, c) - l
            mecha_sup = h - max(o, c)
            rango_total = h - l
            
            if rango_total > 0:
                es_martillo = (cuerpo < (rango_total * 0.3) and 
                              mecha_inf > (cuerpo * 2) and 
                              mecha_sup < cuerpo)
                if es_martillo:
                    martillos += 1
            
            # Detectar rachas alcistas de 3
            if i <= total_velas - 2 and idx >= 2:
                if (candles[idx].close > candles[idx].open and
                    candles[idx-1].close > candles[idx-1].open and
                    candles[idx-2].close > candles[idx-2].open):
                    racha_alcista += 1
        
        # Calcular probabilidades (5 patrones como TradingView)
        total_analizadas = alcistas + bajistas + neutras
        
        p_alcista = alcistas / total_analizadas if total_analizadas > 0 else 0
        p_bajista = bajistas / total_analizadas if total_analizadas > 0 else 0
        p_neutra = neutras / total_analizadas if total_analizadas > 0 else 0
        p_martillo = martillos / total_analizadas if total_analizadas > 0 else 0
        p_racha_alcista = racha_alcista / (total_analizadas - 2) if total_analizadas >= 3 else 0
        
        return {
            'p_alcista': p_alcista,
            'p_bajista': p_bajista,
            'p_neutra': p_neutra,
            'p_martillo': p_martillo,
            'p_racha_alcista': p_racha_alcista
        }
    
    def _count_consecutive_against_pattern(self, candles: List[Candle], pattern_type: str) -> int:
        """Cuenta velas consecutivas que van contra el patrón dominante"""
        count = 0
        max_count = 7  # Máximo 7 gales
        
        # Revisar últimas velas de más reciente a más antigua
        for i in range(len(candles) - 1, -1, -1):
            candle = candles[i]
            is_green = candle.close > candle.open
            is_red = candle.close < candle.open
            
            if pattern_type == 'Alcista':
                # Si patrón es alcista, contamos velas rojas (contra tendencia)
                if is_red:
                    count += 1
                else:
                    break  # Termina la racha
            elif pattern_type == 'Bajista':
                # Si patrón es bajista, contamos velas verdes (contra tendencia)
                if is_green:
                    count += 1
                else:
                    break
            
            if count >= max_count:
                break
        
        return min(count, max_count)
    
    def _detect_reversal_pattern(self, candles: List[Candle]) -> Optional[str]:
        """Detecta patrón de reversión: 3+ velas del mismo color y cambia
        
        Returns:
            'R' si hay reversión alcista (3+ rojas + 1 verde)
            'V' si hay reversión bajista (3+ verdes + 1 roja)
            None si no hay patrón
        """
        if len(candles) < 4:
            return None
        
        # Última vela cerrada
        ultima = candles[-1]
        ultima_es_verde = ultima.close > ultima.open
        ultima_es_roja = ultima.close < ultima.open
        
        # Contar velas consecutivas anteriores del mismo color
        count_rojas = 0
        count_verdes = 0
        
        for i in range(len(candles) - 2, -1, -1):
            candle = candles[i]
            if candle.close < candle.open:
                count_rojas += 1
                if count_verdes > 0:
                    break
            elif candle.close > candle.open:
                count_verdes += 1
                if count_rojas > 0:
                    break
            else:
                break
        
        # Reversión alcista: 3+ rojas + 1 verde
        if count_rojas >= 3 and ultima_es_verde:
            return 'R'
        
        # Reversión bajista: 3+ verdes + 1 roja  
        if count_verdes >= 3 and ultima_es_roja:
            return 'V'
        
        return None
    
    def _generate_signal_logic(self, candles: List[Candle], analysis: dict) -> Optional[Signal]:
        """Genera señal basada en patrón dominante - LÓGICA PROBABILÍSTICA
        
        Lógica correcta:
        1. La señal se genera con la vela ACTUAL/EN CURSO (la última)
        2. El análisis probabilístico usa las 100 velas PASADAS
        3. Precio de entrada = OPEN de la vela actual
        4. No importa el color de la vela actual (aún está en progreso)
        5. La señal es válida durante toda la vela (5 minutos completos)
        """
        if len(candles) < 2:
            return None
            
        # VELA ACTUAL (la que está en curso ahora)
        vela_actual = candles[-1]
        precio_entrada = vela_actual.open
        timestamp_entrada = vela_actual.time
        
        # Última vela CERRADA (para referencia en logs)
        vela_anterior = candles[-2]
        vela_anterior_verde = vela_anterior.close > vela_anterior.open
        vela_anterior_roja = vela_anterior.close < vela_anterior.open
        
        # Extraer las 5 probabilidades
        p_alcista = analysis['p_alcista']
        p_bajista = analysis['p_bajista']
        p_neutra = analysis['p_neutra']
        p_martillo = analysis['p_martillo']
        p_racha_alcista = analysis['p_racha_alcista']
        
        # LÓGICA TRADINGVIEW: Encontrar patrón con MAYOR probabilidad entre los 5
        probs = {
            'Alcista': p_alcista,
            'Bajista': p_bajista,
            'Neutra': p_neutra,
            'Martillo': p_martillo,
            'Racha Alcista x3': p_racha_alcista
        }
        
        max_prob_nombre = max(probs.keys(), key=lambda k: probs[k])
        max_prob_valor = probs[max_prob_nombre]
        
        # Detectar patrón de reversión (3+ velas + cambio)
        reversal_marker = self._detect_reversal_pattern(candles[:-1])
        
        # Logs de debug detallados
        vela_ant_tipo = "🟢 VERDE" if vela_anterior_verde else ("🔴 ROJA" if vela_anterior_roja else "⚪ DOJI")
        print(f"📊 Análisis Tablero Binarias (5 Patrones):")
        print(f"   P_Alcista: {p_alcista:.1%} | P_Bajista: {p_bajista:.1%} | P_Neutra: {p_neutra:.1%}")
        print(f"   P_Martillo: {p_martillo:.1%} | P_Racha x3: {p_racha_alcista:.1%}")
        print(f"   Patrón MAYOR: {max_prob_nombre} ({max_prob_valor:.1%})")
        print(f"   Última vela cerrada: {vela_ant_tipo} (open={vela_anterior.open:.5f}, close={vela_anterior.close:.5f})")
        print(f"   🎯 Vela ACTUAL: Precio entrada = {precio_entrada:.5f}")
        if reversal_marker:
            print(f"   🔄 Indicador Reversión: {reversal_marker}")
        
        # LÓGICA SIEMPRE ACTIVA: Sistema SIEMPRE genera señal (CALL o PUT)
        # El usuario requiere que siempre haya operaciones activas
        direction = 'HOLD'
        confidence = max_prob_valor
        
        # Patrones ALCISTAS → CALL
        if max_prob_nombre in ['Alcista', 'Martillo', 'Racha Alcista x3']:
            direction = 'CALL'
            print(f"   ✅ SEÑAL CALL: Patrón {max_prob_nombre} ({max_prob_valor:.1%})")
        
        # Patrón BAJISTA → PUT
        elif max_prob_nombre == 'Bajista':
            direction = 'PUT'
            print(f"   ✅ SEÑAL PUT: Patrón Bajista ({max_prob_valor:.1%})")
        
        # Patrón NEUTRO → Decidir según segunda mayor probabilidad
        elif max_prob_nombre == 'Neutra':
            # Comparar Alcista vs Bajista (ignorar Neutra)
            if p_alcista >= p_bajista:
                direction = 'CALL'
                confidence = p_alcista
                print(f"   ✅ SEÑAL CALL: Patrón Neutro → Segundo patrón Alcista ({p_alcista:.1%})")
            else:
                direction = 'PUT'
                confidence = p_bajista
                print(f"   ✅ SEÑAL PUT: Patrón Neutro → Segundo patrón Bajista ({p_bajista:.1%})")
        
        # Mínimo de confianza: 48% para asegurar que hay una tendencia clara
        if confidence < 0.48:
            confidence = 0.48  # Confianza mínima visual (no afecta señal)
        
        # Indicadores
        indicators = {
            'close': precio_entrada,  # Precio de entrada (open de vela actual)
            'patron': max_prob_nombre,
            'probabilidad': max_prob_valor,
            'reversal_marker': reversal_marker
        }
        
        return Signal(
            symbol='',
            timeframe='',
            strategy_name='',
            direction=direction,
            confidence=confidence,
            timestamp=timestamp_entrada,  # Timestamp de la vela actual
            indicators=indicators
        )
