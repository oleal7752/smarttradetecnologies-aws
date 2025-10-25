"""
Motor de Backtesting - STC Trading System
Simula estrategias con datos históricos y calcula métricas de rendimiento
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from strategy_engine import Strategy, Candle, Trade, Signal


@dataclass
class BacktestResult:
    """Resultado completo de un backtest"""
    strategy_name: str
    symbol: str
    timeframe: str
    start_time: int
    end_time: int
    initial_balance: float
    final_balance: float
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    draw_trades: int = 0
    
    total_profit: float = 0.0
    total_loss: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    
    sharpe_ratio: float = 0.0
    
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    
    def calculate_metrics(self):
        """Calcula todas las métricas de rendimiento"""
        if self.total_trades == 0:
            return
        
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
        
        self.profit_factor = abs(self.gross_profit / self.gross_loss) if self.gross_loss != 0 else 0
        
        self.average_win = self.gross_profit / self.winning_trades if self.winning_trades > 0 else 0
        self.average_loss = abs(self.gross_loss / self.losing_trades) if self.losing_trades > 0 else 0
        
        self._calculate_drawdown()
        
        self._calculate_sharpe_ratio()
        
    def _calculate_drawdown(self):
        """Calcula el máximo drawdown"""
        if len(self.equity_curve) < 2:
            return
            
        peak = self.equity_curve[0]
        max_dd = 0
        max_dd_pct = 0
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
                
        self.max_drawdown = max_dd
        self.max_drawdown_percent = max_dd_pct
        
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0):
        """Calcula el Sharpe Ratio"""
        if len(self.equity_curve) < 2:
            self.sharpe_ratio = 0.0
            return
            
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        
        if len(returns) == 0 or np.std(returns) == 0:
            self.sharpe_ratio = 0.0
            return
            
        excess_returns = returns - risk_free_rate
        self.sharpe_ratio = float(np.mean(excess_returns) / np.std(returns) * np.sqrt(252))
        
    def to_dict(self) -> dict:
        """Convierte el resultado a diccionario"""
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'initial_balance': self.initial_balance,
            'final_balance': self.final_balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'draw_trades': self.draw_trades,
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'total_profit': round(self.total_profit, 2),
            'total_loss': round(self.total_loss, 2),
            'average_win': round(self.average_win, 2),
            'average_loss': round(self.average_loss, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_drawdown_percent': round(self.max_drawdown_percent, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'net_profit': round(self.final_balance - self.initial_balance, 2),
            'return_percent': round(((self.final_balance - self.initial_balance) / self.initial_balance) * 100, 2)
        }


class BacktestingEngine:
    """Motor de backtesting para probar estrategias con datos históricos"""
    
    def __init__(self, initial_balance: float = 1000.0, trade_amount: float = 1.0, payout_percent: float = 85.0):
        self.initial_balance = initial_balance
        self.trade_amount = trade_amount
        self.payout_percent = payout_percent
        
    def run_backtest(
        self, 
        strategy: Strategy, 
        symbol: str, 
        timeframe: str, 
        candles: List[Candle],
        trade_duration: int = 5
    ) -> BacktestResult:
        """
        Ejecuta un backtest completo de una estrategia
        
        Args:
            strategy: La estrategia a probar
            symbol: Par de trading
            timeframe: Temporalidad (M1, M5, etc.)
            candles: Datos históricos de velas
            trade_duration: Duración de cada trade en minutos
            
        Returns:
            BacktestResult con todas las métricas calculadas
        """
        result = BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            timeframe=timeframe,
            start_time=candles[0].time,
            end_time=candles[-1].time,
            initial_balance=self.initial_balance,
            final_balance=self.initial_balance
        )
        
        current_balance = self.initial_balance
        result.equity_curve.append(current_balance)
        
        consecutive_wins = 0
        consecutive_losses = 0
        
        min_candles = strategy.min_candles
        
        for i in range(min_candles, len(candles) - trade_duration):
            window = candles[max(0, i - 200):i + 1]
            
            signal = strategy.analyze(symbol, timeframe, window)
            
            if signal and signal.confidence >= 0.7:
                entry_candle = candles[i]
                exit_candle = candles[i + trade_duration]
                
                entry_price = entry_candle.close
                exit_price = exit_candle.close
                
                price_change = exit_price - entry_price
                
                if signal.direction == 'CALL':
                    win = price_change > 0
                elif signal.direction == 'PUT':
                    win = price_change < 0
                else:
                    continue
                
                if win:
                    profit = self.trade_amount * (self.payout_percent / 100)
                    trade_result = 'WIN'
                    result.winning_trades += 1
                    result.gross_profit += profit
                    consecutive_wins += 1
                    consecutive_losses = 0
                    
                    if consecutive_wins > result.max_consecutive_wins:
                        result.max_consecutive_wins = consecutive_wins
                    
                    if profit > result.largest_win:
                        result.largest_win = profit
                        
                elif abs(price_change) < 0.00001:
                    profit = 0
                    trade_result = 'DRAW'
                    result.draw_trades += 1
                    consecutive_wins = 0
                    consecutive_losses = 0
                    
                else:
                    profit = -self.trade_amount
                    trade_result = 'LOSS'
                    result.losing_trades += 1
                    result.gross_loss += profit
                    consecutive_losses += 1
                    consecutive_wins = 0
                    
                    if consecutive_losses > result.max_consecutive_losses:
                        result.max_consecutive_losses = consecutive_losses
                    
                    if abs(profit) > abs(result.largest_loss):
                        result.largest_loss = profit
                
                current_balance += profit
                result.equity_curve.append(current_balance)
                
                trade = Trade(
                    id=f"bt_{result.total_trades}",
                    symbol=symbol,
                    direction=signal.direction,
                    amount=self.trade_amount,
                    duration=trade_duration,
                    entry_price=entry_price,
                    entry_time=entry_candle.time,
                    exit_price=exit_price,
                    exit_time=exit_candle.time,
                    profit=profit,
                    result=trade_result,
                    strategy_name=strategy.name
                )
                
                result.trades.append(trade)
                result.total_trades += 1
                result.total_profit += profit
        
        result.final_balance = current_balance
        result.calculate_metrics()
        
        return result
    
    def compare_strategies(
        self, 
        strategies: List[Strategy], 
        symbol: str, 
        timeframe: str, 
        candles: List[Candle]
    ) -> List[BacktestResult]:
        """Compara múltiples estrategias con los mismos datos"""
        results = []
        
        for strategy in strategies:
            result = self.run_backtest(strategy, symbol, timeframe, candles)
            results.append(result)
            
        results.sort(key=lambda x: x.final_balance, reverse=True)
        
        return results


if __name__ == '__main__':
    print("📊 Backtesting Engine - STC Trading System")
    print("Motor de backtesting con métricas profesionales")
