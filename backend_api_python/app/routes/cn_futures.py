"""
CN Futures API Routes
中国股指期货 API 路由

Endpoints:
- GET /contracts - Get contract list / 获取合约列表
- GET /quote - Get real-time quote / 获取实时行情
- GET /kline - Get K-line data / 获取K线数据
- POST /calculate/margin - Calculate margin / 计算保证金
- POST /calculate/fee - Calculate fee / 计算手续费
- GET /strategy/status - Get strategy status / 获取策略状态
- POST /strategy/start - Start strategy / 启动策略
- POST /strategy/stop - Stop strategy / 停止策略
- GET /strategy/config - Get strategy config / 获取策略配置
- PUT /strategy/config - Update strategy config / 更新策略配置
- GET /strategy/trades - Get trade records / 获取交易记录
- GET /strategy/pnl - Get P&L statistics / 获取盈亏统计

Author: QuantDinger
Created: 2026-02-04
"""

from flask import Blueprint, request, jsonify
import traceback

from app.utils.logger import get_logger
from app.utils.auth import login_required, get_current_user_id

logger = get_logger(__name__)

cn_futures_bp = Blueprint('cn_futures', __name__)

# ==================== Helper Functions ====================

def get_data_source():
    """Get CN Futures data source instance"""
    from app.data_sources.cn_futures import CNFuturesDataSource, AKSHARE_AVAILABLE
    if not AKSHARE_AVAILABLE:
        raise RuntimeError("akshare not installed")
    return CNFuturesDataSource()

def get_calculator():
    """Get Futures calculator instance"""
    from app.services.futures_calculator import FuturesCalculator
    return FuturesCalculator()

def get_models():
    """Get Futures model classes"""
    from app.models.futures import (
        FuturesStrategyConfig,
        FuturesPosition,
        FuturesTrade,
        FuturesSignal
    )
    return FuturesStrategyConfig, FuturesPosition, FuturesTrade, FuturesSignal


# ==================== Basic Data Endpoints ====================

@cn_futures_bp.route('/contracts', methods=['GET'])
@login_required
def get_contracts():
    """
    Get contract list
    获取合约列表
    
    Returns:
        List of available contracts with specifications
    """
    try:
        data_source = get_data_source()
        
        contracts = []
        for product, info in data_source.PRODUCTS.items():
            # Get main contract code
            try:
                main_code = data_source.get_main_contract_code(product)
            except:
                main_code = f"{product}0"
            
            contracts.append({
                'symbol': f"{product}0",  # Main contract symbol
                'actual_code': main_code,
                'product': product,
                'name': info['name'],
                'multiplier': info['multiplier'],
                'margin_ratio': info['margin_ratio'],
                'tick_size': info['tick_size']
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': contracts
        })
        
    except Exception as e:
        logger.error(f"Failed to get contracts: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get contracts: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/quote', methods=['GET'])
@login_required
def get_quote():
    """
    Get real-time quote
    获取实时行情
    
    Query params:
        symbol: Contract symbol (IC0, IM0, IF0, IH0, or specific like IC2503)
        
    Returns:
        Quote data including last price, bid/ask, volume
    """
    try:
        symbol = request.args.get('symbol', 'IC0')
        
        data_source = get_data_source()
        ticker = data_source.get_ticker(symbol)
        
        if not ticker or ticker.get('last', 0) == 0:
            return jsonify({
                'code': 0,
                'msg': 'No quote data available',
                'data': None
            })
        
        # Get contract info
        contract_info = data_source.get_contract_info(symbol)
        
        # Calculate additional info
        calculator = get_calculator()
        margin_info = calculator.margin.calculate(symbol, ticker['last'], 1)
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                **ticker,
                'contract_info': contract_info,
                'margin_required': margin_info.margin_required,
                'contract_value': margin_info.contract_value
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get quote: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get quote: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/kline', methods=['GET'])
@login_required
def get_kline():
    """
    Get K-line data
    获取K线数据
    
    Query params:
        symbol: Contract symbol
        timeframe: Time period (1m, 5m, 15m, 30m, 1H, 1D)
        limit: Number of bars (default 300, max 1000)
        
    Returns:
        K-line data list
    """
    try:
        symbol = request.args.get('symbol', 'IC0')
        timeframe = request.args.get('timeframe', '1D')
        limit = min(int(request.args.get('limit', 300)), 1000)
        before_time = request.args.get('before_time')
        
        if before_time:
            before_time = int(before_time)
        
        data_source = get_data_source()
        klines = data_source.get_kline(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            before_time=before_time
        )
        
        if not klines:
            return jsonify({
                'code': 0,
                'msg': 'No K-line data available',
                'data': []
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': klines
        })
        
    except Exception as e:
        logger.error(f"Failed to get kline: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get kline: {str(e)}',
            'data': None
        }), 500


# ==================== Calculation Endpoints ====================

@cn_futures_bp.route('/calculate/margin', methods=['POST'])
@login_required
def calculate_margin():
    """
    Calculate margin
    计算保证金
    
    Body:
        symbol: Contract symbol
        price: Price
        quantity: Number of contracts (default 1)
        
    Returns:
        Margin calculation result
    """
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'IC0')
        price = float(data.get('price', 0))
        quantity = int(data.get('quantity', 1))
        
        if price <= 0:
            return jsonify({
                'code': 0,
                'msg': 'Invalid price',
                'data': None
            }), 400
        
        calculator = get_calculator()
        margin_info = calculator.margin.calculate(symbol, price, quantity)
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'contract_value': margin_info.contract_value,
                'margin_ratio': margin_info.margin_ratio,
                'margin_required': margin_info.margin_required,
                'multiplier': margin_info.multiplier
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to calculate margin: {e}")
        return jsonify({
            'code': 0,
            'msg': f'Calculation failed: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/calculate/fee', methods=['POST'])
@login_required
def calculate_fee():
    """
    Calculate fee
    计算手续费
    
    Body:
        symbol: Contract symbol
        price: Transaction price
        quantity: Number of contracts
        is_open: Is opening position (default true)
        is_close_today: Is closing today's position (default false)
        
    Returns:
        Fee calculation result
    """
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'IC0')
        price = float(data.get('price', 0))
        quantity = int(data.get('quantity', 1))
        is_open = data.get('is_open', True)
        is_close_today = data.get('is_close_today', False)
        
        if price <= 0:
            return jsonify({
                'code': 0,
                'msg': 'Invalid price',
                'data': None
            }), 400
        
        calculator = get_calculator()
        fee_info = calculator.fee.calculate(
            symbol=symbol,
            price=price,
            quantity=quantity,
            is_open=is_open,
            is_close_today=is_close_today
        )
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'contract_value': fee_info.contract_value,
                'fee_rate': fee_info.fee_rate,
                'fee_amount': round(fee_info.fee_amount, 2),
                'is_close_today': fee_info.is_close_today
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to calculate fee: {e}")
        return jsonify({
            'code': 0,
            'msg': f'Calculation failed: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/calculate/trade-cost', methods=['POST'])
@login_required
def calculate_trade_cost():
    """
    Calculate complete trade cost
    计算完整交易成本
    
    Body:
        symbol: Contract symbol
        entry_price: Entry price
        exit_price: Exit price
        quantity: Number of contracts
        is_same_day: Is same day trade
        
    Returns:
        Complete trade cost calculation
    """
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'IC0')
        entry_price = float(data.get('entry_price', 0))
        exit_price = float(data.get('exit_price', 0))
        quantity = int(data.get('quantity', 1))
        is_same_day = data.get('is_same_day', True)
        
        if entry_price <= 0 or exit_price <= 0:
            return jsonify({
                'code': 0,
                'msg': 'Invalid prices',
                'data': None
            }), 400
        
        calculator = get_calculator()
        result = calculator.calculate_trade_cost(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            is_same_day=is_same_day
        )
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Failed to calculate trade cost: {e}")
        return jsonify({
            'code': 0,
            'msg': f'Calculation failed: {str(e)}',
            'data': None
        }), 500


# ==================== Strategy Control Endpoints ====================

@cn_futures_bp.route('/strategy/status', methods=['GET'])
@login_required
def get_strategy_status():
    """
    Get strategy status
    获取策略状态
    
    Returns:
        Strategy running status and summary info
    """
    try:
        user_id = get_current_user_id()
        FuturesStrategyConfig, FuturesPosition, FuturesTrade, FuturesSignal = get_models()
        
        # Get config
        config = FuturesStrategyConfig.get_config(user_id)
        if not config:
            # Create default config
            from app.models.futures import insert_default_config
            insert_default_config(user_id)
            config = FuturesStrategyConfig.get_config(user_id)
        
        # Get positions
        positions = FuturesPosition.get_positions(user_id, status='open')
        
        # Get today's signal count
        signal_count = FuturesSignal.get_today_signal_count(user_id)
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'is_running': config.get('is_running', False) if config else False,
                'monitoring_start': config.get('monitoring_start', '09:30') if config else '09:30',
                'monitoring_end': config.get('monitoring_end', '15:00') if config else '15:00',
                'today_signal_count': signal_count,
                'open_position_count': len(positions),
                'positions_summary': [
                    {
                        'symbol': p['symbol'],
                        'direction': p['direction'],
                        'quantity': p['quantity'],
                        'entry_price': float(p['entry_price'])
                    }
                    for p in positions[:5]  # Limit to 5
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get strategy status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get status: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/start', methods=['POST'])
@login_required
def start_strategy():
    """
    Start strategy
    启动策略
    
    Body:
        config: Optional strategy config to save before starting
        
    Returns:
        Start result
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        FuturesStrategyConfig, _, _, _ = get_models()
        
        # Optionally update config
        if 'config' in data:
            FuturesStrategyConfig.save_config(user_id, data['config'])
        
        # Set running status
        success = FuturesStrategyConfig.set_running_status(user_id, True)
        
        if success:
            # TODO: Actually start the strategy executor
            # from app.services.futures_strategy_executor import FuturesStrategyExecutor
            # executor = FuturesStrategyExecutor()
            # executor.start(user_id)
            
            return jsonify({
                'code': 1,
                'msg': 'Strategy started',
                'data': {'is_running': True}
            })
        else:
            return jsonify({
                'code': 0,
                'msg': 'Failed to start strategy',
                'data': None
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to start strategy: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to start: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/stop', methods=['POST'])
@login_required
def stop_strategy():
    """
    Stop strategy
    停止策略
    
    Returns:
        Stop result
    """
    try:
        user_id = get_current_user_id()
        FuturesStrategyConfig, _, _, _ = get_models()
        
        # Set running status
        success = FuturesStrategyConfig.set_running_status(user_id, False)
        
        if success:
            # TODO: Actually stop the strategy executor
            
            return jsonify({
                'code': 1,
                'msg': 'Strategy stopped',
                'data': {'is_running': False}
            })
        else:
            return jsonify({
                'code': 0,
                'msg': 'Failed to stop strategy',
                'data': None
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to stop strategy: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to stop: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/config', methods=['GET'])
@login_required
def get_strategy_config():
    """
    Get strategy configuration
    获取策略配置
    
    Returns:
        Strategy configuration
    """
    try:
        user_id = get_current_user_id()
        FuturesStrategyConfig, _, _, _ = get_models()
        
        config = FuturesStrategyConfig.get_config(user_id)
        
        if not config:
            # Return default config
            import json
            return jsonify({
                'code': 1,
                'msg': 'success',
                'data': {
                    'symbols': ['IC0', 'IM0', 'IF0', 'IH0'],
                    'drop_threshold_1': -2.0,
                    'drop_threshold_2': -3.0,
                    'monitoring_start': '09:30',
                    'monitoring_end': '15:00',
                    'max_position': 1,
                    'notification_channels': ['browser'],
                    'telegram_chat_id': '',
                    'wechat_webhook': '',
                    'is_running': False
                }
            })
        
        # Parse JSON fields
        import json
        symbols = config.get('symbols', '["IC0","IM0","IF0","IH0"]')
        if isinstance(symbols, str):
            symbols = json.loads(symbols)
        
        notification_channels = config.get('notification_channels', '["browser"]')
        if isinstance(notification_channels, str):
            notification_channels = json.loads(notification_channels)
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'symbols': symbols,
                'drop_threshold_1': float(config.get('drop_threshold_1', -2.0)),
                'drop_threshold_2': float(config.get('drop_threshold_2', -3.0)),
                'monitoring_start': config.get('monitoring_start', '09:30'),
                'monitoring_end': config.get('monitoring_end', '15:00'),
                'max_position': config.get('max_position', 1),
                'notification_channels': notification_channels,
                'telegram_chat_id': config.get('telegram_chat_id', ''),
                'wechat_webhook': config.get('wechat_webhook', ''),
                'is_running': config.get('is_running', False)
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get strategy config: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get config: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/config', methods=['PUT'])
@login_required
def update_strategy_config():
    """
    Update strategy configuration
    更新策略配置
    
    Body:
        Configuration fields to update
        
    Returns:
        Update result
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        FuturesStrategyConfig, _, _, _ = get_models()
        
        success = FuturesStrategyConfig.save_config(user_id, data)
        
        if success:
            return jsonify({
                'code': 1,
                'msg': 'Configuration updated',
                'data': None
            })
        else:
            return jsonify({
                'code': 0,
                'msg': 'Failed to update configuration',
                'data': None
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to update strategy config: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to update: {str(e)}',
            'data': None
        }), 500


# ==================== Data Query Endpoints ====================

@cn_futures_bp.route('/strategy/trades', methods=['GET'])
@login_required
def get_strategy_trades():
    """
    Get trade records
    获取交易记录
    
    Query params:
        limit: Number of records (default 50)
        offset: Offset for pagination (default 0)
        symbol: Filter by symbol (optional)
        
    Returns:
        Trade records list
    """
    try:
        user_id = get_current_user_id()
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        symbol = request.args.get('symbol')
        
        _, _, FuturesTrade, _ = get_models()
        
        trades = FuturesTrade.get_trades(
            user_id=user_id,
            limit=limit,
            offset=offset,
            symbol=symbol
        )
        
        # Format response
        formatted_trades = []
        for trade in trades:
            formatted_trades.append({
                'id': trade['id'],
                'symbol': trade['symbol'],
                'trade_type': trade['trade_type'],
                'price': float(trade['price']),
                'quantity': trade['quantity'],
                'margin': float(trade.get('margin', 0)),
                'fee': float(trade.get('fee', 0)),
                'pnl': float(trade.get('pnl', 0)),
                'signal_reason': trade.get('signal_reason', ''),
                'trade_time': str(trade['trade_time']) if trade.get('trade_time') else None
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'trades': formatted_trades,
                'total': len(formatted_trades),  # TODO: Get actual total count
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get trades: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/positions', methods=['GET'])
@login_required
def get_strategy_positions():
    """
    Get positions
    获取持仓
    
    Query params:
        status: Position status (open/closed/all, default open)
        
    Returns:
        Positions list
    """
    try:
        user_id = get_current_user_id()
        status = request.args.get('status', 'open')
        
        _, FuturesPosition, _, _ = get_models()
        
        positions = FuturesPosition.get_positions(user_id=user_id, status=status)
        
        # Format response
        formatted_positions = []
        for pos in positions:
            formatted_positions.append({
                'id': pos['id'],
                'symbol': pos['symbol'],
                'direction': pos['direction'],
                'quantity': pos['quantity'],
                'entry_price': float(pos['entry_price']),
                'entry_time': str(pos['entry_time']) if pos.get('entry_time') else None,
                'status': pos['status'],
                'close_price': float(pos['close_price']) if pos.get('close_price') else None,
                'close_time': str(pos['close_time']) if pos.get('close_time') else None,
                'realized_pnl': float(pos.get('realized_pnl', 0))
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': formatted_positions
        })
        
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get positions: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/pnl', methods=['GET'])
@login_required
def get_strategy_pnl():
    """
    Get P&L statistics
    获取盈亏统计
    
    Query params:
        period: Time period (day/week/month/year, default month)
        
    Returns:
        P&L summary and history
    """
    try:
        user_id = get_current_user_id()
        period = request.args.get('period', 'month')
        
        _, _, FuturesTrade, _ = get_models()
        
        # Get summary
        summary = FuturesTrade.get_pnl_summary(user_id=user_id, period=period)
        
        # Get history
        days_map = {'day': 1, 'week': 7, 'month': 30, 'year': 365}
        days = days_map.get(period, 30)
        history = FuturesTrade.get_pnl_history(user_id=user_id, days=days)
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'summary': summary,
                'history': history
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get pnl: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get pnl: {str(e)}',
            'data': None
        }), 500


@cn_futures_bp.route('/strategy/signals', methods=['GET'])
@login_required
def get_strategy_signals():
    """
    Get signal records
    获取信号记录
    
    Query params:
        limit: Number of records (default 50)
        symbol: Filter by symbol (optional)
        executed: Filter by execution status (optional)
        
    Returns:
        Signal records list
    """
    try:
        user_id = get_current_user_id()
        limit = min(int(request.args.get('limit', 50)), 200)
        symbol = request.args.get('symbol')
        executed = request.args.get('executed')
        
        if executed is not None:
            executed = executed.lower() == 'true'
        
        _, _, _, FuturesSignal = get_models()
        
        signals = FuturesSignal.get_signals(
            user_id=user_id,
            limit=limit,
            symbol=symbol,
            executed=executed
        )
        
        # Format response
        formatted_signals = []
        for sig in signals:
            formatted_signals.append({
                'id': sig['id'],
                'symbol': sig['symbol'],
                'signal_type': sig['signal_type'],
                'trigger_price': float(sig['trigger_price']),
                'base_price': float(sig['base_price']) if sig.get('base_price') else None,
                'drop_pct': float(sig['drop_pct']) if sig.get('drop_pct') else None,
                'is_executed': sig.get('is_executed', False),
                'signal_time': str(sig['signal_time']) if sig.get('signal_time') else None
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': formatted_signals
        })
        
    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': f'Failed to get signals: {str(e)}',
            'data': None
        }), 500
