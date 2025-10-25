"""
Rutas API para gestión de bots y estrategias - STC Trading System
Multi-tenant: Cada usuario ve solo sus propios bots
"""

from flask import Blueprint, request, jsonify, current_app, session
from typing import List
from functools import wraps
from strategy_engine import StrategyEngine, Candle
from database import (
    get_db, Bot as BotModel, BotStat as BotStatsModel, Trade as TradeModel,
    BacktestRun, BacktestTrade, BacktestEquityPoint,
    BacktestMasterRun, BacktestMasterSignal
)
from auth_routes import requires_active_access
from strategies import (
    RSIStrategy, 
    MACDStrategy, 
    BollingerStrategy,
    ProbabilityGaleStrategy,
    KolmogorovMarkovStrategy,
    KolmogorovComplexityStrategy,
    SmartTradeAcademyStrategy,
    TableroBinariasStrategy,
    TendencialTradeStrategy
)
from backtesting_engine import BacktestingEngine
from auto_trading_bot import BotManager, BotConfig
import traceback
import requests
import logging

logger = logging.getLogger(__name__)

bot_bp = Blueprint('bot', __name__)


def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'No autorizado - Debe iniciar sesión'}), 401
        return f(*args, **kwargs)
    return decorated_function


strategy_engine = StrategyEngine()
bot_manager = BotManager(strategy_engine)

# Configurar proveedores de datos y trading
def trade_executor(symbol: str, direction: str, amount: float, duration: int):
    """Ejecuta un trade usando la API de IQ Option"""
    try:
        response = requests.post('http://localhost:5002/api/iq/trade', json={
            'symbol': symbol,
            'direction': direction,
            'amount': amount,
            'duration': duration
        }, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {'success': False, 'error': f'Error {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def candle_provider(symbol: str, timeframe: str, limit: int = 200):
    """Obtiene velas usando la API de IQ Option"""
    try:
        response = requests.get('http://localhost:5002/api/iq/candles', params={
            'symbol': symbol,
            'timeframe': timeframe,
            'limit': limit
        }, timeout=10)
        
        if response.status_code == 200:
            candles_data = response.json()
            # Convertir a objetos Candle
            candles = []
            for c in candles_data:
                candles.append(Candle(
                    time=c.get('time', 0),
                    open=c.get('open', 0.0),
                    high=c.get('high', 0.0),
                    low=c.get('low', 0.0),
                    close=c.get('close', 0.0),
                    volume=c.get('volume', 0.0)
                ))
            return candles
        else:
            return []
    except Exception as e:
        logger.error(f"Error obteniendo velas: {e}")
        return []

def result_checker(trade_id: str):
    """Verifica el resultado de un trade"""
    try:
        response = requests.get(f'http://localhost:5002/api/iq/order_results', timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            return results.get(trade_id)
        else:
            return None
    except Exception as e:
        logger.error(f"Error verificando resultado: {e}")
        return None

# Configurar providers en el bot manager
bot_manager.set_trade_executor(trade_executor)
bot_manager.set_candle_provider(candle_provider)
bot_manager.set_result_checker(result_checker)

strategy_engine.register_strategy(RSIStrategy())
strategy_engine.register_strategy(MACDStrategy())
strategy_engine.register_strategy(BollingerStrategy())
strategy_engine.register_strategy(ProbabilityGaleStrategy())
strategy_engine.register_strategy(KolmogorovMarkovStrategy())
strategy_engine.register_strategy(KolmogorovComplexityStrategy())
strategy_engine.register_strategy(SmartTradeAcademyStrategy())
strategy_engine.register_strategy(TableroBinariasStrategy())
strategy_engine.register_strategy(TendencialTradeStrategy())

logger.info("9 estrategias registradas en el motor de trading")
logger.info("Trade executor y candle provider configurados correctamente")

# Cargar bots guardados desde disco
bot_manager.load_bots()


@bot_bp.route('/api/signals/tablero', methods=['GET'])
def get_tablero_signals():
    """Genera señales de Tablero Binarias para el gráfico"""
    try:
        symbol = request.args.get('symbol', 'EURUSD-OTC')
        timeframe = request.args.get('timeframe', 'M5')
        
        # Obtener velas
        candles = candle_provider(symbol, timeframe, 200)
        
        if not candles or len(candles) < 10:
            return jsonify({'success': False, 'error': 'No hay suficientes velas'}), 400
        
        # CRÍTICO: Crear instancia SEPARADA para dashboard (no compartir con bot)
        # El bot usa strategy_engine.strategies['Tablero Binarias']
        # El dashboard usa esta instancia independiente para evitar conflictos de estado
        tablero_strategy = TableroBinariasStrategy()
        
        # Generar señales para cada vela
        signals = []
        
        # Analizar las últimas 50 velas para detectar señales
        for i in range(len(candles) - 50, len(candles)):
            if i < 10:
                continue
                
            candles_subset = candles[:i+1]
            signal = tablero_strategy.analyze(symbol, timeframe, candles_subset)
            
            if signal and signal.direction != 'HOLD':
                # Obtener timestamp de la vela (compatible con dict o objeto Candle)
                candle_data = candles[i]
                if isinstance(candle_data, dict):
                    # Velas de IQ usan "from", velas de objetos usan "time"
                    candle_time = candle_data.get('from') or candle_data.get('time', 0)
                    candle_close = candle_data.get('close', 0)
                else:
                    # Objeto Candle
                    candle_time = getattr(candle_data, 'from', None) or getattr(candle_data, 'time', 0)
                    candle_close = getattr(candle_data, 'close', 0)
                
                # CRÍTICO: Validar que el timestamp sea válido (no 0, no None)
                if not candle_time or candle_time <= 0:
                    continue
                
                signals.append({
                    'time': int(candle_time),
                    'direction': signal.direction,
                    'confidence': signal.confidence,
                    'price': float(candle_close),
                    'pattern': signal.indicators.get('patron', ''),
                    'probability': signal.indicators.get('probabilidad', 0),
                    'is_gale': signal.indicators.get('is_gale', False),
                    'gale_level': signal.indicators.get('gale_level', 0)
                })
        
        return jsonify({
            'success': True,
            'signals': signals
        })
        
    except Exception as e:
        logger.error(f"Error generando señales Tablero: {e}")
        import traceback
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/strategies/list', methods=['GET'])
def get_strategies():
    """Obtiene lista de todas las estrategias disponibles"""
    try:
        strategies = strategy_engine.get_all_strategies()
        return jsonify({'success': True, 'strategies': strategies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/strategies/activate', methods=['POST'])
def activate_strategy():
    """Activa una estrategia para trading en vivo"""
    try:
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        
        if not strategy_name:
            return jsonify({'success': False, 'error': 'strategy_name requerido'}), 400
            
        strategy_engine.activate_strategy(strategy_name)
        
        return jsonify({'success': True, 'message': f'Estrategia {strategy_name} activada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/strategies/deactivate', methods=['POST'])
def deactivate_strategy():
    """Desactiva una estrategia"""
    try:
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        
        if not strategy_name:
            return jsonify({'success': False, 'error': 'strategy_name requerido'}), 400
            
        strategy_engine.deactivate_strategy(strategy_name)
        
        return jsonify({'success': True, 'message': f'Estrategia {strategy_name} desactivada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/strategies/analyze', methods=['POST'])
def analyze_with_strategy():
    """Analiza mercado con una estrategia específica"""
    try:
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', 'M5')
        candles_data = data.get('candles', [])
        
        if not all([strategy_name, symbol, candles_data]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
            
        strategy = strategy_engine.strategies.get(strategy_name)
        if not strategy:
            return jsonify({'success': False, 'error': 'Estrategia no encontrada'}), 404
            
        candles = [Candle(**c) for c in candles_data]
        
        signal = strategy.analyze(symbol, timeframe, candles)
        
        if signal:
            return jsonify({
                'success': True,
                'has_signal': True,
                'signal': signal.to_dict()
            })
        else:
            return jsonify({
                'success': True,
                'has_signal': False,
                'message': 'No hay señal en este momento'
            })
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/backtest/run', methods=['POST'])
@login_required
def run_backtest():
    """Ejecuta un backtest de una estrategia y guarda los resultados en BD"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', 'M5')
        candles_data = data.get('candles', [])
        initial_balance = data.get('initial_balance', 1000.0)
        trade_amount = data.get('trade_amount', 1.0)
        payout_percent = data.get('payout_percent', 85.0)
        trade_duration = data.get('trade_duration', 5)
        
        if not all([strategy_name, symbol, candles_data]):
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
            
        strategy = strategy_engine.strategies.get(strategy_name)
        if not strategy:
            return jsonify({'success': False, 'error': 'Estrategia no encontrada'}), 404
            
        candles = [Candle(**c) for c in candles_data]
        
        backtester = BacktestingEngine(
            initial_balance=initial_balance,
            trade_amount=trade_amount,
            payout_percent=payout_percent
        )
        
        result = backtester.run_backtest(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            trade_duration=trade_duration
        )
        
        # Guardar resultado del backtest en la base de datos
        with get_db() as db:
            # Crear BacktestRun
            backtest_run = BacktestRun(
                user_id=user_id,
                strategy_name=result.strategy_name,
                symbol=result.symbol,
                timeframe=result.timeframe,
                initial_balance=result.initial_balance,
                trade_amount=trade_amount,
                payout_percent=payout_percent,
                trade_duration=trade_duration,
                start_time=result.start_time,
                end_time=result.end_time,
                final_balance=result.final_balance,
                total_trades=result.total_trades,
                winning_trades=result.winning_trades,
                losing_trades=result.losing_trades,
                draw_trades=result.draw_trades,
                win_rate=result.win_rate,
                profit_factor=result.profit_factor,
                net_profit=result.final_balance - result.initial_balance,
                return_percent=((result.final_balance - result.initial_balance) / result.initial_balance) * 100,
                total_profit=result.total_profit,
                total_loss=result.total_loss,
                gross_profit=result.gross_profit,
                gross_loss=result.gross_loss,
                average_win=result.average_win,
                average_loss=result.average_loss,
                largest_win=result.largest_win,
                largest_loss=result.largest_loss,
                max_drawdown=result.max_drawdown,
                max_drawdown_percent=result.max_drawdown_percent,
                sharpe_ratio=result.sharpe_ratio,
                max_consecutive_wins=result.max_consecutive_wins,
                max_consecutive_losses=result.max_consecutive_losses
            )
            db.add(backtest_run)
            db.flush()  # Obtener el ID generado
            
            # Guardar trades individuales
            for trade in result.trades:
                backtest_trade = BacktestTrade(
                    backtest_run_id=backtest_run.id,
                    trade_id=trade.id,
                    symbol=trade.symbol,
                    direction=trade.direction,
                    amount=trade.amount,
                    duration=trade.duration,
                    entry_price=trade.entry_price,
                    entry_time=trade.entry_time,
                    exit_price=trade.exit_price,
                    exit_time=trade.exit_time,
                    result=trade.result,
                    profit=trade.profit,
                    strategy_name=trade.strategy_name
                )
                db.add(backtest_trade)
            
            # Guardar puntos de equity curve
            for idx, balance in enumerate(result.equity_curve):
                equity_point = BacktestEquityPoint(
                    backtest_run_id=backtest_run.id,
                    point_index=idx,
                    balance=balance,
                    timestamp=result.start_time + (idx * 60 * 5) if idx < len(result.equity_curve) else None
                )
                db.add(equity_point)
            
            db.commit()
            
            return jsonify({
                'success': True,
                'backtest_id': backtest_run.id,
                'result': result.to_dict(),
                'trades': [t.to_dict() for t in result.trades[:100]],
                'message': f'Backtest ejecutado y guardado con ID {backtest_run.id}'
            })
        
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/list', methods=['GET'])
@login_required
def get_bots():
    """Obtiene lista de bots del usuario actual (multi-tenant)"""
    try:
        user_id = session['user_id']
        
        with get_db() as db:
            user_bots = db.query(BotModel).filter_by(user_id=user_id).all()
            
            bots_data = []
            for bot_model in user_bots:
                # Verificar si el bot está activo en el manager
                bot_instance = bot_manager.bots.get(bot_model.id)
                is_running = bot_instance is not None and bot_instance.running
                
                bots_data.append({
                    'id': bot_model.id,
                    'name': bot_model.name,
                    'strategy': bot_model.strategy_name,
                    'symbol': bot_model.symbol,
                    'timeframe': bot_model.timeframe,
                    'running': is_running,
                    'trade_amount': bot_model.trade_amount,
                    'created_at': bot_model.created_at.isoformat() if bot_model.created_at else None,
                    'use_dual_gale': bot_model.use_dual_gale
                })
            
            return jsonify({'success': True, 'bots': bots_data})
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/create', methods=['POST'])
@login_required
@requires_active_access
def create_bot():
    """Crea un nuevo bot de trading para el usuario actual (requiere acceso activo)"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        config = BotConfig(
            name=data.get('name'),
            strategy_name=data.get('strategy_name'),
            symbol=data.get('symbol'),
            timeframe=data.get('timeframe', 'M5'),
            trade_amount=data.get('trade_amount', 1.0),
            trade_duration=data.get('trade_duration', 5),
            max_daily_loss=data.get('max_daily_loss', 10.0),
            max_daily_trades=data.get('max_daily_trades', 20),
            auto_restart=data.get('auto_restart', True),
            use_dual_gale=data.get('use_dual_gale', False)
        )
        
        bot_id = bot_manager.create_bot(config, user_id=user_id)
        
        return jsonify({
            'success': True,
            'bot_id': bot_id,
            'message': 'Bot creado exitosamente'
        })
        
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/start/<bot_id>', methods=['POST'])
@login_required
@requires_active_access
def start_bot(bot_id):
    """Inicia un bot (solo si pertenece al usuario y tiene acceso activo)"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        logger.info(f"Iniciando bot {bot_id} para usuario {user_id}")
        logger.debug(f"Bots en manager: {list(bot_manager.bots.keys())}")
        
        if bot_id in bot_manager.bots:
            bot = bot_manager.bots[bot_id]
            logger.debug(f"Bot encontrado: {bot.config.name}, running: {bot.running}")
            bot_manager.start_bot(bot_id)
            logger.info(f"Bot {bot_id} iniciado exitosamente")
        else:
            logger.error(f"Bot {bot_id} no existe en manager")
            return jsonify({'success': False, 'error': 'Bot no cargado en memoria'}), 500
            
        return jsonify({'success': True, 'message': 'Bot iniciado'})
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/stop/<bot_id>', methods=['POST'])
@login_required
def stop_bot(bot_id):
    """Detiene un bot (solo si pertenece al usuario)"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        bot_manager.stop_bot(bot_id)
        return jsonify({'success': True, 'message': 'Bot detenido'})
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/delete/<bot_id>', methods=['DELETE'])
@login_required
def delete_bot(bot_id):
    """Elimina un bot (solo si pertenece al usuario)"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        bot_manager.delete_bot(bot_id)
        return jsonify({'success': True, 'message': 'Bot eliminado'})
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/stats/<bot_id>', methods=['GET'])
@login_required
def get_bot_stats(bot_id):
    """Obtiene estadísticas de un bot (solo si pertenece al usuario)"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        stats = bot_manager.get_bot_stats(bot_id)
        if stats:
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'error': 'Bot no encontrado'}), 404
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/gale_stats/<bot_id>', methods=['GET'])
@login_required
def get_bot_gale_stats(bot_id):
    """Obtiene estadísticas de gales de un bot (solo si pertenece al usuario)"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        bot = bot_manager.bots.get(bot_id)
        if not bot:
            return jsonify({'success': False, 'error': 'Bot no encontrado'}), 404
        
        if hasattr(bot, 'get_stats'):
            stats = bot.get_stats()
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'error': 'Bot no tiene sistema de gales'}), 400
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/bots/signals/<bot_id>', methods=['GET'])
@login_required
@requires_active_access
def get_bot_signals(bot_id):
    """Obtiene señales activas de un bot (solo si pertenece al usuario)
    REQUIERE: Suscripción activa o código promocional válido"""
    try:
        user_id = session['user_id']
        
        # Verificar ownership del bot
        with get_db() as db:
            bot_model = db.query(BotModel).filter_by(id=bot_id, user_id=user_id).first()
            if not bot_model:
                return jsonify({'success': False, 'error': 'Bot no encontrado o sin permisos'}), 404
        
        bot = bot_manager.bots.get(bot_id)
        if not bot:
            return jsonify({'success': False, 'error': 'Bot no encontrado'}), 404
        
        if not bot.stats.last_signal:
            return jsonify({
                'success': True,
                'has_signal': False,
                'message': 'Sin señales activas'
            })
        
        signal = bot.stats.last_signal
        return jsonify({
            'success': True,
            'has_signal': True,
            'signal': {
                'direction': signal.direction,
                'confidence': signal.confidence,
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'timeframe': signal.timeframe,
                'strategy': signal.strategy_name,
                'indicators': signal.indicators
            }
        })
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/monitor/all', methods=['GET'])
@login_required
def get_all_bots_monitor():
    """Obtiene estadísticas de monitoreo de los bots del usuario (multi-tenant)"""
    try:
        user_id = session['user_id']
        all_stats = []
        
        # Solo mostrar bots del usuario
        with get_db() as db:
            user_bot_ids = [bot.id for bot in db.query(BotModel).filter_by(user_id=user_id).all()]
        
        for bot_id in user_bot_ids:
            bot = bot_manager.bots.get(bot_id)
            if bot:
                bot_data = {
                    'bot_id': bot_id,
                    'config': bot.get_config(),
                    'running': bot.running
                }
                
                if hasattr(bot, 'get_stats'):
                    bot_data['stats'] = bot.get_stats()
                else:
                    bot_data['stats'] = {'bot_stats': bot.stats.to_dict()}
                
                all_stats.append(bot_data)
        
        return jsonify({'success': True, 'bots': all_stats})
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/backtest/list', methods=['GET'])
@login_required
def list_backtests():
    """Obtiene lista de backtests del usuario"""
    try:
        user_id = session['user_id']
        
        with get_db() as db:
            backtests = db.query(BacktestRun).filter_by(user_id=user_id).order_by(
                BacktestRun.created_at.desc()
            ).all()
            
            backtest_list = []
            for bt in backtests:
                backtest_list.append({
                    'id': bt.id,
                    'strategy_name': bt.strategy_name,
                    'symbol': bt.symbol,
                    'timeframe': bt.timeframe,
                    'initial_balance': bt.initial_balance,
                    'final_balance': bt.final_balance,
                    'net_profit': bt.net_profit,
                    'return_percent': bt.return_percent,
                    'total_trades': bt.total_trades,
                    'win_rate': bt.win_rate,
                    'profit_factor': bt.profit_factor,
                    'max_drawdown_percent': bt.max_drawdown_percent,
                    'sharpe_ratio': bt.sharpe_ratio,
                    'created_at': bt.created_at.isoformat() if bt.created_at else None
                })
            
            return jsonify({'success': True, 'backtests': backtest_list})
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/backtest/<int:backtest_id>', methods=['GET'])
@login_required
def get_backtest_details(backtest_id):
    """Obtiene detalles completos de un backtest incluyendo trades y equity curve"""
    try:
        user_id = session['user_id']
        
        with get_db() as db:
            # Verificar que el backtest pertenece al usuario
            backtest = db.query(BacktestRun).filter_by(
                id=backtest_id,
                user_id=user_id
            ).first()
            
            if not backtest:
                return jsonify({'success': False, 'error': 'Backtest no encontrado'}), 404
            
            # Obtener trades
            trades = db.query(BacktestTrade).filter_by(
                backtest_run_id=backtest_id
            ).order_by(BacktestTrade.entry_time).all()
            
            # Obtener equity curve
            equity_points = db.query(BacktestEquityPoint).filter_by(
                backtest_run_id=backtest_id
            ).order_by(BacktestEquityPoint.point_index).all()
            
            trades_data = [{
                'id': t.trade_id,
                'symbol': t.symbol,
                'direction': t.direction,
                'amount': t.amount,
                'duration': t.duration,
                'entry_price': t.entry_price,
                'entry_time': t.entry_time,
                'exit_price': t.exit_price,
                'exit_time': t.exit_time,
                'result': t.result,
                'profit': t.profit,
                'strategy_name': t.strategy_name
            } for t in trades]
            
            equity_data = [{
                'index': ep.point_index,
                'balance': ep.balance,
                'timestamp': ep.timestamp
            } for ep in equity_points]
            
            backtest_data = {
                'id': backtest.id,
                'strategy_name': backtest.strategy_name,
                'symbol': backtest.symbol,
                'timeframe': backtest.timeframe,
                'initial_balance': backtest.initial_balance,
                'trade_amount': backtest.trade_amount,
                'payout_percent': backtest.payout_percent,
                'trade_duration': backtest.trade_duration,
                'start_time': backtest.start_time,
                'end_time': backtest.end_time,
                'final_balance': backtest.final_balance,
                'total_trades': backtest.total_trades,
                'winning_trades': backtest.winning_trades,
                'losing_trades': backtest.losing_trades,
                'draw_trades': backtest.draw_trades,
                'win_rate': backtest.win_rate,
                'profit_factor': backtest.profit_factor,
                'net_profit': backtest.net_profit,
                'return_percent': backtest.return_percent,
                'total_profit': backtest.total_profit,
                'total_loss': backtest.total_loss,
                'gross_profit': backtest.gross_profit,
                'gross_loss': backtest.gross_loss,
                'average_win': backtest.average_win,
                'average_loss': backtest.average_loss,
                'largest_win': backtest.largest_win,
                'largest_loss': backtest.largest_loss,
                'max_drawdown': backtest.max_drawdown,
                'max_drawdown_percent': backtest.max_drawdown_percent,
                'sharpe_ratio': backtest.sharpe_ratio,
                'max_consecutive_wins': backtest.max_consecutive_wins,
                'max_consecutive_losses': backtest.max_consecutive_losses,
                'created_at': backtest.created_at.isoformat() if backtest.created_at else None
            }
            
            return jsonify({
                'success': True,
                'backtest': backtest_data,
                'trades': trades_data,
                'equity_curve': equity_data
            })
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/symbols/available', methods=['GET'])
def get_available_symbols():
    """Obtiene símbolos disponibles con velas en la BD y sus rangos de fechas"""
    try:
        from sqlalchemy import text
        
        with get_db() as db:
            query = text("""
                SELECT 
                    symbol,
                    source,
                    COUNT(*) as total_candles,
                    to_timestamp(MIN(timestamp)) as date_from,
                    to_timestamp(MAX(timestamp)) as date_to,
                    ARRAY_AGG(DISTINCT DATE(to_timestamp(timestamp))) as available_dates
                FROM candles
                GROUP BY symbol, source
                ORDER BY total_candles DESC
            """)
            
            result = db.execute(query)
            symbols_data = []
            
            for row in result:
                symbols_data.append({
                    'symbol': row[0],
                    'source': row[1],
                    'total_candles': row[2],
                    'date_from': row[3].isoformat() if row[3] else None,
                    'date_to': row[4].isoformat() if row[4] else None,
                    'available_dates': [d.isoformat() for d in (row[5] or [])]
                })
            
            return jsonify({'success': True, 'symbols': symbols_data})
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


@bot_bp.route('/api/candles/backtest', methods=['GET'])
def get_candles_for_backtest():
    """Obtiene velas desde BD para backtesting (sin requerir acceso activo)"""
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', 'M5')
        limit = int(request.args.get('limit', 5000))
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Symbol is required'}), 400
        
        with get_db() as db:
            if date_from and date_to:
                from_timestamp = int(datetime.fromisoformat(date_from).timestamp())
                to_timestamp = int(datetime.fromisoformat(date_to + 'T23:59:59').timestamp())
                
                query = text("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM candles
                    WHERE symbol = :symbol AND timeframe = :timeframe
                      AND timestamp >= :from_ts AND timestamp <= :to_ts
                    ORDER BY timestamp ASC
                    LIMIT :limit
                """)
                
                result = db.execute(query, {
                    'symbol': symbol, 
                    'timeframe': timeframe, 
                    'from_ts': from_timestamp,
                    'to_ts': to_timestamp,
                    'limit': limit
                })
            else:
                query = text("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM candles
                    WHERE symbol = :symbol AND timeframe = :timeframe
                    ORDER BY timestamp ASC
                    LIMIT :limit
                """)
                
                result = db.execute(query, {'symbol': symbol, 'timeframe': timeframe, 'limit': limit})
            
            candles = []
            for row in result:
                candles.append({
                    'time': row[0],
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5]) if row[5] else 0.0
                })
            
            return jsonify(candles)
            
    except Exception as e:
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': str(e)}), 500


def init_bot_system(trade_executor, candle_provider):
    """Inicializa el sistema de bots con funciones de ejecución"""
    bot_manager.set_trade_executor(trade_executor)
    bot_manager.set_candle_provider(candle_provider)
    logger.info("Sistema de bots inicializado")


@bot_bp.route('/api/user/performance', methods=['GET'])
@login_required
def get_user_performance():
    """Obtiene estadísticas de rendimiento del usuario para gráficas"""
    try:
        user_id = session.get('user_id')
        
        with get_db() as db:
            # Profit over time (últimos 30 días)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.timestamp >= thirty_days_ago
            ).order_by(Trade.timestamp).all()
            
            # Calcular profit acumulado por día
            daily_profit = {}
            cumulative_profit = 0
            
            for trade in trades:
                date_key = trade.timestamp.strftime('%Y-%m-%d')
                profit = trade.profit if trade.profit else 0
                cumulative_profit += profit
                
                if date_key not in daily_profit:
                    daily_profit[date_key] = cumulative_profit
                else:
                    daily_profit[date_key] = cumulative_profit
            
            profit_over_time = [
                {'date': date, 'profit': profit} 
                for date, profit in sorted(daily_profit.items())
            ]
            
            # Estadísticas generales
            total_trades = db.query(Trade).filter_by(user_id=user_id).count()
            winning_trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.result == 'win'
            ).count()
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_profit = db.query(func.sum(Trade.profit)).filter_by(user_id=user_id).scalar() or 0
            
            # Distribución de Gales
            gale_distribution = db.query(
                Trade.gale_level,
                func.count(Trade.id).label('count')
            ).filter_by(user_id=user_id).group_by(Trade.gale_level).all()
            
            gale_dist_data = [
                {'gale': f'Gale {gale}', 'count': count} 
                for gale, count in gale_distribution
            ]
            
            # Estadísticas por bot
            bot_stats = db.query(BotStat).filter_by(user_id=user_id).all()
            
            return jsonify({
                'success': True,
                'performance': {
                    'profit_over_time': profit_over_time,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': round(win_rate, 2),
                    'total_profit': float(total_profit),
                    'gale_distribution': gale_dist_data,
                    'active_bots': len([s for s in bot_stats if s.status == 'running'])
                }
            }), 200
            
    except Exception as e:
        import traceback
        logger.exception("Error capturado:")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@bot_bp.route('/api/backtest/master/list', methods=['GET'])
def list_master_backtests():
    """Lista todos los backtests maestros disponibles - Endpoint público para demo/marketing"""
    try:
        with get_db() as db:
            master_runs = db.query(BacktestMasterRun).filter_by(
                is_active=True
            ).order_by(
                BacktestMasterRun.created_at.desc()
            ).all()
            
            results = []
            for run in master_runs:
                results.append({
                    'id': run.id,
                    'strategy_name': run.strategy_name,
                    'symbol': run.symbol,
                    'timeframe': run.timeframe,
                    'version': run.version,
                    'total_candles': run.total_candles,
                    'total_signals': run.total_signals,
                    'win_rate': round(run.win_rate, 2),
                    'start_time': run.start_time,
                    'end_time': run.end_time,
                    'created_at': run.created_at.isoformat(),
                    'description': run.description
                })
            
            return jsonify({
                'success': True,
                'master_backtests': results
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bot_bp.route('/api/backtest/master/<int:master_id>', methods=['GET'])
def get_master_backtest(master_id):
    """Obtiene backtest maestro con recalculo dinámico de métricas - Endpoint público para demo/marketing"""
    try:
        user_amount = float(request.args.get('amount', 100.0))
        user_payout = float(request.args.get('payout', 85.0))
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        with get_db() as db:
            master_run = db.query(BacktestMasterRun).filter_by(id=master_id).first()
            
            if not master_run:
                return jsonify({
                    'success': False,
                    'error': 'Backtest maestro no encontrado'
                }), 404
            
            query = db.query(BacktestMasterSignal).filter_by(master_run_id=master_id)
            
            if date_from:
                from datetime import datetime as dt
                date_from_ts = int(dt.strptime(date_from, '%Y-%m-%d').timestamp())
                query = query.filter(BacktestMasterSignal.signal_time >= date_from_ts)
            
            if date_to:
                from datetime import datetime as dt
                date_to_ts = int(dt.strptime(date_to + 'T23:59:59', '%Y-%m-%dT%H:%M:%S').timestamp())
                query = query.filter(BacktestMasterSignal.signal_time <= date_to_ts)
            
            signals = query.order_by(BacktestMasterSignal.signal_time.asc()).all()
            
            if not signals:
                return jsonify({
                    'success': False,
                    'error': 'No hay señales en el rango seleccionado'
                }), 404
            
            current_balance = 1000.0
            initial_balance = 1000.0
            equity_curve = [current_balance]
            
            winning_count = 0
            losing_count = 0
            draw_count = 0
            
            total_profit = 0.0
            gross_profit = 0.0
            gross_loss = 0.0
            
            largest_win = 0.0
            largest_loss = 0.0
            
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            
            trades_list = []
            
            for signal in signals:
                if signal.result == 'WIN':
                    profit = user_amount * (user_payout / 100)
                    winning_count += 1
                    gross_profit += profit
                    consecutive_wins += 1
                    consecutive_losses = 0
                    
                    if consecutive_wins > max_consecutive_wins:
                        max_consecutive_wins = consecutive_wins
                    
                    if profit > largest_win:
                        largest_win = profit
                        
                elif signal.result == 'DRAW':
                    profit = 0.0
                    draw_count += 1
                    consecutive_wins = 0
                    consecutive_losses = 0
                    
                else:
                    profit = -user_amount
                    losing_count += 1
                    gross_loss += profit
                    consecutive_losses += 1
                    consecutive_wins = 0
                    
                    if consecutive_losses > max_consecutive_losses:
                        max_consecutive_losses = consecutive_losses
                    
                    if abs(profit) > abs(largest_loss):
                        largest_loss = profit
                
                current_balance += profit
                total_profit += profit
                equity_curve.append(current_balance)
                
                trades_list.append({
                    'signal_index': signal.signal_index,
                    'time': signal.signal_time,
                    'direction': signal.direction,
                    'entry_price': signal.entry_price,
                    'exit_price': signal.exit_price,
                    'result': signal.result,
                    'profit': round(profit, 2)
                })
            
            total_trades = len(signals)
            win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0
            profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
            average_win = gross_profit / winning_count if winning_count > 0 else 0
            average_loss = abs(gross_loss / losing_count) if losing_count > 0 else 0
            
            peak = initial_balance
            max_drawdown = 0
            max_drawdown_percent = 0
            
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                
                dd = peak - equity
                dd_pct = (dd / peak) * 100 if peak > 0 else 0
                
                if dd > max_drawdown:
                    max_drawdown = dd
                    max_drawdown_percent = dd_pct
            
            return jsonify({
                'success': True,
                'master_backtest': {
                    'id': master_run.id,
                    'strategy_name': master_run.strategy_name,
                    'symbol': master_run.symbol,
                    'timeframe': master_run.timeframe,
                    'version': master_run.version
                },
                'parameters': {
                    'amount': user_amount,
                    'payout': user_payout,
                    'initial_balance': initial_balance
                },
                'metrics': {
                    'total_trades': total_trades,
                    'winning_trades': winning_count,
                    'losing_trades': losing_count,
                    'draw_trades': draw_count,
                    'win_rate': round(win_rate, 2),
                    'profit_factor': round(profit_factor, 2),
                    'total_profit': round(total_profit, 2),
                    'final_balance': round(current_balance, 2),
                    'net_profit': round(current_balance - initial_balance, 2),
                    'return_percent': round(((current_balance - initial_balance) / initial_balance) * 100, 2),
                    'gross_profit': round(gross_profit, 2),
                    'gross_loss': round(gross_loss, 2),
                    'average_win': round(average_win, 2),
                    'average_loss': round(average_loss, 2),
                    'largest_win': round(largest_win, 2),
                    'largest_loss': round(largest_loss, 2),
                    'max_drawdown': round(max_drawdown, 2),
                    'max_drawdown_percent': round(max_drawdown_percent, 2),
                    'max_consecutive_wins': max_consecutive_wins,
                    'max_consecutive_losses': max_consecutive_losses
                },
                'equity_curve': [round(e, 2) for e in equity_curve],
                'trades': trades_list
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
