"""
Market Scanner - Escanea múltiples pares para encontrar las mejores oportunidades
Analiza pares mayores y menores con estrategias RSI, MACD y Bollinger
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategy_engine import Candle
from services.twelvedata_service import twelvedata_service
import time

class MarketScanner:
    """Escáner de mercado que analiza múltiples pares simultáneamente"""
    
    def __init__(self):
        # Pares mayores (más líquidos, spreads bajos)
        self.major_pairs = [
            "EURUSD",  # Euro/Dólar
            "GBPUSD",  # Libra/Dólar
            "USDJPY",  # Dólar/Yen
            "USDCHF",  # Dólar/Franco Suizo
            "AUDUSD",  # Dólar Australiano/Dólar
            "USDCAD",  # Dólar/Dólar Canadiense
        ]
        
        # Pares menores (cruces sin USD, más volatilidad)
        self.minor_pairs = [
            "EURGBP",  # Euro/Libra
            "EURJPY",  # Euro/Yen
            "GBPJPY",  # Libra/Yen
            "EURCHF",  # Euro/Franco Suizo
            "AUDJPY",  # Dólar Australiano/Yen
            "NZDUSD",  # Dólar Neozelandés/Dólar
        ]
        
        # Estrategias para análisis
        self.strategies = [
            RSIStrategy(),
            MACDStrategy(),
            BollingerStrategy()
        ]
        
        print("🔍 Market Scanner inicializado")
        print(f"   📊 Pares mayores: {len(self.major_pairs)}")
        print(f"   📊 Pares menores: {len(self.minor_pairs)}")
        print(f"   🎯 Estrategias: {len(self.strategies)}")
    
    def analyze_pair(self, symbol: str) -> Optional[Dict]:
        """
        Analiza un par y retorna su puntuación de oportunidad
        
        Returns:
            {
                'symbol': str,
                'score': float (0-100),
                'direction': 'CALL' o 'PUT',
                'confidence': float (0-1),
                'signals': [lista de señales por estrategia],
                'consensus': str (descripción del consenso)
            }
        """
        try:
            # Obtener velas M5 (50 velas = ~4 horas)
            candles_data = twelvedata_service.get_candles(symbol, 'M5', 50)
            
            if not candles_data or len(candles_data) < 50:
                print(f"⚠️  {symbol}: Datos insuficientes ({len(candles_data) if candles_data else 0} velas)")
                return None
            
            # Convertir a objetos Candle
            candles = [
                Candle(
                    time=c['time'],
                    open=c['open'],
                    high=c['high'],
                    low=c['low'],
                    close=c['close'],
                    volume=c.get('volume', 0)
                ) for c in candles_data
            ]
            
            # Analizar con cada estrategia
            signals = []
            call_votes = 0
            put_votes = 0
            total_confidence = 0
            
            for strategy in self.strategies:
                if len(candles) >= strategy.min_candles:
                    indicators = strategy.calculate_indicators(candles)
                    signal = strategy.generate_signal(candles, indicators)
                    
                    if signal:
                        signal.symbol = symbol
                        signal.timeframe = 'M5'
                        signals.append({
                            'strategy': strategy.name,
                            'direction': signal.direction,
                            'confidence': signal.confidence,
                            'indicators': signal.indicators
                        })
                        
                        if signal.direction == 'CALL':
                            call_votes += 1
                        else:
                            put_votes += 1
                        
                        total_confidence += signal.confidence
            
            # Si no hay señales fuertes, analizar tendencia general
            if not signals:
                # Calcular tendencia simple (precio actual vs promedio 20 velas)
                closes = [c.close for c in candles]
                current_price = closes[-1]
                avg_20 = sum(closes[-20:]) / 20
                
                if current_price > avg_20:
                    direction = 'CALL'
                    confidence = 0.5
                else:
                    direction = 'PUT'
                    confidence = 0.5
                
                return {
                    'symbol': symbol,
                    'score': 40,  # Score bajo para tendencia simple
                    'direction': direction,
                    'confidence': confidence,
                    'signals': [{
                        'strategy': 'Trend Analysis',
                        'direction': direction,
                        'confidence': confidence,
                        'indicators': {'price': current_price, 'avg_20': avg_20}
                    }],
                    'consensus': f"Tendencia {direction} (sin señales fuertes)",
                    'votes': {'CALL': 1 if direction == 'CALL' else 0, 'PUT': 0 if direction == 'CALL' else 1}
                }
            
            # Calcular consenso
            total_votes = call_votes + put_votes
            direction = 'CALL' if call_votes > put_votes else 'PUT'
            consensus_ratio = max(call_votes, put_votes) / total_votes
            avg_confidence = total_confidence / len(signals)
            
            # Puntuación final (0-100)
            # Factores: consenso de estrategias (60%) + confianza promedio (40%)
            score = (consensus_ratio * 60) + (avg_confidence * 40)
            
            # Descripción del consenso
            if consensus_ratio >= 0.75:
                consensus = f"Fuerte {direction}"
            elif consensus_ratio >= 0.6:
                consensus = f"Moderado {direction}"
            else:
                consensus = "Mixto - señales contradictorias"
            
            return {
                'symbol': symbol,
                'score': round(score, 2),
                'direction': direction,
                'confidence': round(avg_confidence, 3),
                'signals': signals,
                'consensus': consensus,
                'votes': {
                    'CALL': call_votes,
                    'PUT': put_votes
                }
            }
            
        except Exception as e:
            print(f"❌ Error analizando {symbol}: {e}")
            return None
    
    def scan_market(self, include_majors=True, include_minors=True, top_n=5) -> List[Dict]:
        """
        Escanea el mercado y retorna las mejores oportunidades
        
        Args:
            include_majors: Incluir pares mayores
            include_minors: Incluir pares menores
            top_n: Número de mejores oportunidades a retornar
        
        Returns:
            Lista de oportunidades ordenadas por score (mayor a menor)
        """
        print("\n🔍 === ESCANEANDO MERCADO ===")
        
        # Lista de pares a analizar
        pairs_to_scan = []
        if include_majors:
            pairs_to_scan.extend(self.major_pairs)
        if include_minors:
            pairs_to_scan.extend(self.minor_pairs)
        
        print(f"📊 Analizando {len(pairs_to_scan)} pares...")
        
        opportunities = []
        
        for i, symbol in enumerate(pairs_to_scan, 1):
            print(f"\n[{i}/{len(pairs_to_scan)}] Analizando {symbol}...")
            
            result = self.analyze_pair(symbol)
            if result:
                opportunities.append(result)
                print(f"✅ {symbol}: Score {result['score']:.1f} | {result['consensus']} | Conf {result['confidence']:.2f}")
            
            # Delay para no saturar la API (300ms entre requests)
            if i < len(pairs_to_scan):
                time.sleep(0.3)
        
        # Ordenar por score (mayor a menor)
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        # Retornar top N
        top_opportunities = opportunities[:top_n]
        
        print(f"\n🎯 === TOP {len(top_opportunities)} OPORTUNIDADES ===")
        for i, opp in enumerate(top_opportunities, 1):
            print(f"\n{i}. {opp['symbol']} - Score: {opp['score']:.1f}")
            print(f"   📈 Dirección: {opp['direction']}")
            print(f"   💪 Confianza: {opp['confidence']:.1%}")
            print(f"   🎯 Consenso: {opp['consensus']}")
            print(f"   📊 Votos: CALL {opp['votes']['CALL']} | PUT {opp['votes']['PUT']}")
            print(f"   🔧 Estrategias activas: {len(opp['signals'])}")
        
        return top_opportunities


# Función CLI para pruebas
def main():
    scanner = MarketScanner()
    
    # Escanear pares mayores y menores, obtener top 5
    opportunities = scanner.scan_market(
        include_majors=True,
        include_minors=True,
        top_n=5
    )
    
    print(f"\n\n✅ Escaneo completado: {len(opportunities)} oportunidades encontradas")
    

if __name__ == "__main__":
    main()
