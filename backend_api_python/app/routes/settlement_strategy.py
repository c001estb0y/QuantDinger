"""
Settlement Arbitrage Strategy API Routes.

Provides REST API endpoints for controlling and monitoring
the Settlement Arbitrage Strategy.
"""

from datetime import datetime, date
from flask import Blueprint, jsonify, request

from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig
from app.strategies.settlement_arbitrage.scheduler import (
    StrategyScheduler, get_scheduler, create_scheduler
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

settlement_strategy_bp = Blueprint('settlement_strategy', __name__)


def _get_running_scheduler():
    """Helper to get the running scheduler or return error."""
    scheduler = get_scheduler()
    if scheduler is None:
        return None, jsonify({
            'success': False,
            'message': 'Strategy scheduler not initialized. Use POST /start first.'
        }), 404
    return scheduler, None, None


# ========== Strategy Control ==========

@settlement_strategy_bp.route('/status', methods=['GET'])
def get_strategy_status():
    """
    GET /api/settlement-strategy/status
    
    Get the current strategy status including running state,
    positions, risk metrics, and monitoring data.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({
            'success': True,
            'data': {
                'is_running': False,
                'message': 'Strategy not started'
            }
        })
    
    try:
        status = scheduler.get_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting strategy status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/start', methods=['POST'])
def start_strategy():
    """
    POST /api/settlement-strategy/start
    
    Start the strategy with optional configuration.
    
    Request body (optional):
    {
        "symbols": ["IM0", "IC0"],
        "threshold_1": 0.01,
        "threshold_2": 0.02,
        "alert_threshold": 0.008,
        "position_size_1": 1,
        "position_size_2": 1,
        "max_daily_loss": 10000,
        "max_drawdown": 0.05,
        "notification_channels": ["telegram"]
    }
    """
    # Check if already running
    existing = get_scheduler()
    if existing and existing.is_running:
        return jsonify({
            'success': False,
            'message': 'Strategy is already running. Stop it first.'
        }), 409
    
    try:
        data = request.get_json(silent=True) or {}
        
        # Build strategy config
        strategy_config = StrategyConfig(
            symbols=data.get('symbols', ['IM0', 'IC0']),
            threshold_1=data.get('threshold_1', 0.01),
            threshold_2=data.get('threshold_2', 0.02),
            alert_threshold=data.get('alert_threshold', 0.008),
            position_size_1=data.get('position_size_1', 1),
            position_size_2=data.get('position_size_2', 1),
            max_position_per_symbol=data.get('max_position_per_symbol', 2),
            notification_channels=data.get('notification_channels', ['telegram']),
            notify_on_entry=data.get('notify_on_entry', True),
            notify_on_exit=data.get('notify_on_exit', True),
            notify_on_alert=data.get('notify_on_alert', True),
        )
        strategy_config.validate()
        
        # Build risk config
        risk_config = RiskConfig(
            max_daily_loss=data.get('max_daily_loss', 10000),
            max_drawdown=data.get('max_drawdown', 0.05),
            force_close_on_limit=data.get('force_close_on_limit', True),
            max_total_position=data.get('max_total_position', 4),
        )
        risk_config.validate()
        
        # Build notification config
        notification_config = data.get('notification_config', None)
        
        # Create and start scheduler
        scheduler = create_scheduler(
            strategy_config=strategy_config,
            risk_config=risk_config,
            notification_config=notification_config,
        )
        scheduler.start()
        
        return jsonify({
            'success': True,
            'message': 'Strategy started successfully',
            'data': scheduler.get_status()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': f'Invalid config: {e}'}), 400
    except Exception as e:
        logger.error(f"Error starting strategy: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/stop', methods=['POST'])
def stop_strategy():
    """
    POST /api/settlement-strategy/stop
    
    Stop the running strategy.
    """
    scheduler = get_scheduler()
    if scheduler is None or not scheduler.is_running:
        return jsonify({
            'success': False,
            'message': 'Strategy is not running'
        }), 409
    
    try:
        scheduler.stop()
        return jsonify({
            'success': True,
            'message': 'Strategy stopped successfully'
        })
    except Exception as e:
        logger.error(f"Error stopping strategy: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/config', methods=['GET'])
def get_strategy_config():
    """
    GET /api/settlement-strategy/config
    
    Get current strategy configuration.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        # Return default config
        config = StrategyConfig()
        risk = RiskConfig()
    else:
        config = scheduler._config
        risk = scheduler._risk_config
    
    return jsonify({
        'success': True,
        'data': {
            'strategy': {
                'symbols': config.symbols,
                'threshold_1': config.threshold_1,
                'threshold_2': config.threshold_2,
                'alert_threshold': config.alert_threshold,
                'position_size_1': config.position_size_1,
                'position_size_2': config.position_size_2,
                'max_position_per_symbol': config.max_position_per_symbol,
                'notification_channels': config.notification_channels,
                'notify_on_entry': config.notify_on_entry,
                'notify_on_exit': config.notify_on_exit,
                'notify_on_alert': config.notify_on_alert,
            },
            'risk': {
                'max_daily_loss': risk.max_daily_loss,
                'max_drawdown': risk.max_drawdown,
                'force_close_on_limit': risk.force_close_on_limit,
                'max_total_position': risk.max_total_position,
            }
        }
    })


@settlement_strategy_bp.route('/config', methods=['PUT'])
def update_strategy_config():
    """
    PUT /api/settlement-strategy/config
    
    Update strategy configuration (hot-update, no restart needed).
    
    Request body: Same as POST /start
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({
            'success': False,
            'message': 'Strategy not initialized'
        }), 404
    
    try:
        data = request.get_json(silent=True) or {}
        
        strategy_config = None
        risk_config = None
        
        # Update strategy config if provided
        if any(k in data for k in ['symbols', 'threshold_1', 'threshold_2',
                                     'alert_threshold', 'position_size_1']):
            current = scheduler._config
            strategy_config = StrategyConfig(
                symbols=data.get('symbols', current.symbols),
                threshold_1=data.get('threshold_1', current.threshold_1),
                threshold_2=data.get('threshold_2', current.threshold_2),
                alert_threshold=data.get('alert_threshold', current.alert_threshold),
                position_size_1=data.get('position_size_1', current.position_size_1),
                position_size_2=data.get('position_size_2', current.position_size_2),
                max_position_per_symbol=data.get('max_position_per_symbol', current.max_position_per_symbol),
                notification_channels=data.get('notification_channels', current.notification_channels),
                notify_on_entry=data.get('notify_on_entry', current.notify_on_entry),
                notify_on_exit=data.get('notify_on_exit', current.notify_on_exit),
                notify_on_alert=data.get('notify_on_alert', current.notify_on_alert),
            )
            strategy_config.validate()
        
        # Update risk config if provided
        if any(k in data for k in ['max_daily_loss', 'max_drawdown',
                                     'force_close_on_limit', 'max_total_position']):
            current_risk = scheduler._risk_config
            risk_config = RiskConfig(
                max_daily_loss=data.get('max_daily_loss', current_risk.max_daily_loss),
                max_drawdown=data.get('max_drawdown', current_risk.max_drawdown),
                force_close_on_limit=data.get('force_close_on_limit', current_risk.force_close_on_limit),
                max_total_position=data.get('max_total_position', current_risk.max_total_position),
            )
            risk_config.validate()
        
        scheduler.update_config(strategy_config, risk_config)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': f'Invalid config: {e}'}), 400
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== Monitoring ==========

@settlement_strategy_bp.route('/monitor', methods=['GET'])
def get_monitor_data():
    """
    GET /api/settlement-strategy/monitor
    
    Get real-time monitoring data for all symbols.
    Returns: base prices, current prices, drop percentages, VWAP values.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({'success': True, 'data': {'symbols': {}}})
    
    try:
        monitor = scheduler.strategy.get_monitor_data()
        
        # Enhance with real-time quotes
        for symbol in scheduler._config.symbols:
            quote = scheduler._data_source.get_realtime_quote(symbol)
            if quote and symbol in monitor.get('symbols', {}):
                monitor['symbols'][symbol]['realtime'] = {
                    'last': quote.get('last', 0),
                    'change_pct': quote.get('change_pct', 0),
                    'volume': quote.get('volume', 0),
                    'high': quote.get('high', 0),
                    'low': quote.get('low', 0),
                }
        
        monitor['is_trading_time'] = scheduler._data_source.is_trading_time()
        monitor['is_watch_period'] = scheduler._data_source.is_watch_period()
        
        return jsonify({'success': True, 'data': monitor})
    except Exception as e:
        logger.error(f"Error getting monitor data: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/positions', methods=['GET'])
def get_positions():
    """
    GET /api/settlement-strategy/positions
    
    Get current open positions.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({'success': True, 'data': {'positions': [], 'total_margin': 0}})
    
    try:
        positions = scheduler.position_manager.get_current_positions()
        margin = scheduler.position_manager.get_total_margin_used()
        
        return jsonify({
            'success': True,
            'data': {
                'positions': [p.to_dict() for p in positions],
                'total_margin': margin,
                'count': len(positions),
            }
        })
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/signals', methods=['GET'])
def get_signals():
    """
    GET /api/settlement-strategy/signals
    
    Get today's signal records.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({'success': True, 'data': {'signals': []}})
    
    try:
        signals = scheduler.strategy.get_today_signals()
        return jsonify({
            'success': True,
            'data': {
                'signals': signals,
                'count': len(signals),
            }
        })
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== History ==========

@settlement_strategy_bp.route('/trades', methods=['GET'])
def get_trades():
    """
    GET /api/settlement-strategy/trades
    
    Get trade history with optional filters.
    
    Query params:
    - symbol: Filter by symbol
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - page: Page number (default 1)
    - page_size: Items per page (default 20, max 100)
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({
            'success': True,
            'data': {'trades': [], 'total': 0, 'page': 1, 'page_size': 20}
        })
    
    try:
        symbol = request.args.get('symbol')
        start_str = request.args.get('start_date')
        end_str = request.args.get('end_date')
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)
        
        start_date = datetime.fromisoformat(start_str) if start_str else None
        end_date = datetime.fromisoformat(end_str) if end_str else None
        
        trades = scheduler.position_manager.get_trade_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=page * page_size,
        )
        
        # Apply pagination
        total = len(trades)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_trades = trades[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': {
                'trades': [t.to_dict() for t in page_trades],
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/pnl', methods=['GET'])
def get_pnl_summary():
    """
    GET /api/settlement-strategy/pnl
    
    Get P&L summary statistics.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({'success': True, 'data': {}})
    
    try:
        summary = scheduler.position_manager.get_pnl_summary()
        risk_status = scheduler.risk_manager.get_risk_status()
        
        return jsonify({
            'success': True,
            'data': {
                'pnl': summary,
                'risk': risk_status,
            }
        })
    except Exception as e:
        logger.error(f"Error getting PnL summary: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@settlement_strategy_bp.route('/risk-events', methods=['GET'])
def get_risk_events():
    """
    GET /api/settlement-strategy/risk-events
    
    Get risk event history.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        return jsonify({'success': True, 'data': {'events': []}})
    
    try:
        limit = int(request.args.get('limit', 50))
        events = scheduler.risk_manager.get_events(limit=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'events': events,
                'count': len(events),
            }
        })
    except Exception as e:
        logger.error(f"Error getting risk events: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== Backtest ==========

@settlement_strategy_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """
    POST /api/settlement-strategy/backtest
    
    Run a strategy backtest.
    
    Request body:
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "symbols": ["IM0", "IC0"],
        "threshold_1": 0.01,
        "threshold_2": 0.02,
        "initial_capital": 500000
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': 'start_date and end_date are required'
            }), 400
        
        from datetime import date as date_cls
        from app.strategies.settlement_arbitrage.backtest import SettlementStrategyBacktest
        from app.strategies.settlement_arbitrage.config import BacktestConfig
        
        # Build configs
        bt_strategy_config = StrategyConfig(
            symbols=data.get('symbols', ['IM0', 'IC0']),
            threshold_1=data.get('threshold_1', 0.01),
            threshold_2=data.get('threshold_2', 0.02),
            position_size_1=data.get('position_size_1', 1),
            position_size_2=data.get('position_size_2', 1),
        )
        
        bt_config = BacktestConfig(
            initial_capital=data.get('initial_capital', 500000),
            use_minute_data=data.get('use_minute_data', True),
        )
        
        # Run backtest
        engine = SettlementStrategyBacktest()
        report = engine.run(
            start_date=date_cls.fromisoformat(start_date),
            end_date=date_cls.fromisoformat(end_date),
            strategy_config=bt_strategy_config,
            backtest_config=bt_config,
        )
        
        return jsonify({
            'success': True,
            'data': report.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
