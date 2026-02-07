"""
Futures Strategy Models
期货策略数据模型

Tables:
- qd_futures_strategy_config: Strategy configuration / 策略配置
- qd_futures_positions: Positions / 持仓
- qd_futures_trades: Trade records / 交易记录
- qd_futures_signals: Signal records / 信号记录

Author: QuantDinger
Created: 2026-02-04
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ==================== Strategy Config Model ====================

class FuturesStrategyConfig:
    """
    Futures Strategy Configuration Model
    期货策略配置模型
    """
    
    TABLE_NAME = "qd_futures_strategy_config"
    
    @classmethod
    def get_db(cls):
        """Get database connection"""
        return get_db_connection()
    
    @classmethod
    def get_config(cls, user_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get strategy configuration for user
        
        Args:
            user_id: User ID
            
        Returns:
            Config dict or None
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Failed to get futures config: {e}")
            return None
        finally:
            cursor.close()
    
    @classmethod
    def save_config(cls, user_id: int, config: Dict[str, Any]) -> bool:
        """
        Save or update strategy configuration
        
        Args:
            user_id: User ID
            config: Configuration dict
            
        Returns:
            Success status
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            
            # Check if config exists
            cursor.execute(
                f"SELECT id FROM {cls.TABLE_NAME} WHERE user_id = %s",
                (user_id,)
            )
            existing = cursor.fetchone()
            
            symbols_json = json.dumps(config.get('symbols', ['IC0', 'IM0', 'IF0', 'IH0']))
            notification_channels = json.dumps(config.get('notification_channels', ['browser']))
            
            if existing:
                # Update
                cursor.execute(f"""
                    UPDATE {cls.TABLE_NAME} SET
                        symbols = %s,
                        drop_threshold_1 = %s,
                        drop_threshold_2 = %s,
                        monitoring_start = %s,
                        monitoring_end = %s,
                        max_position = %s,
                        notification_channels = %s,
                        telegram_chat_id = %s,
                        wechat_webhook = %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                """, (
                    symbols_json,
                    config.get('drop_threshold_1', -2.0),
                    config.get('drop_threshold_2', -3.0),
                    config.get('monitoring_start', '09:30'),
                    config.get('monitoring_end', '15:00'),
                    config.get('max_position', 1),
                    notification_channels,
                    config.get('telegram_chat_id', ''),
                    config.get('wechat_webhook', ''),
                    user_id
                ))
            else:
                # Insert
                cursor.execute(f"""
                    INSERT INTO {cls.TABLE_NAME}
                    (user_id, symbols, drop_threshold_1, drop_threshold_2,
                     monitoring_start, monitoring_end, max_position,
                     notification_channels, telegram_chat_id, wechat_webhook,
                     is_running, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    user_id,
                    symbols_json,
                    config.get('drop_threshold_1', -2.0),
                    config.get('drop_threshold_2', -3.0),
                    config.get('monitoring_start', '09:30'),
                    config.get('monitoring_end', '15:00'),
                    config.get('max_position', 1),
                    notification_channels,
                    config.get('telegram_chat_id', ''),
                    config.get('wechat_webhook', ''),
                    False
                ))
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save futures config: {e}")
            db.rollback()
            return False
        finally:
            cursor.close()
    
    @classmethod
    def set_running_status(cls, user_id: int, is_running: bool) -> bool:
        """
        Set strategy running status
        
        Args:
            user_id: User ID
            is_running: Running status
            
        Returns:
            Success status
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                f"UPDATE {cls.TABLE_NAME} SET is_running = %s, updated_at = NOW() WHERE user_id = %s",
                (is_running, user_id)
            )
            db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to set running status: {e}")
            db.rollback()
            return False
        finally:
            cursor.close()


# ==================== Position Model ====================

class FuturesPosition:
    """
    Futures Position Model
    期货持仓模型
    """
    
    TABLE_NAME = "qd_futures_positions"
    
    @classmethod
    def get_db(cls):
        """Get database connection"""
        return get_db_connection()
    
    @classmethod
    def get_positions(cls, user_id: int = 1, status: str = 'open') -> List[Dict[str, Any]]:
        """
        Get positions for user
        
        Args:
            user_id: User ID
            status: Position status (open/closed/all)
            
        Returns:
            List of positions
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            
            if status == 'all':
                cursor.execute(
                    f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s ORDER BY entry_time DESC",
                    (user_id,)
                )
            else:
                cursor.execute(
                    f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s AND status = %s ORDER BY entry_time DESC",
                    (user_id, status)
                )
            
            rows = cursor.fetchall()
            if not rows:
                return []
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
        finally:
            cursor.close()
    
    @classmethod
    def add_position(cls, user_id: int, position: Dict[str, Any]) -> Optional[int]:
        """
        Add a new position
        
        Args:
            user_id: User ID
            position: Position data
            
        Returns:
            Position ID or None
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                INSERT INTO {cls.TABLE_NAME}
                (user_id, symbol, direction, quantity, entry_price, entry_time, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                user_id,
                position.get('symbol'),
                position.get('direction', 'long'),
                position.get('quantity', 1),
                position.get('entry_price'),
                position.get('entry_time', datetime.now()),
                'open'
            ))
            
            result = cursor.fetchone()
            db.commit()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to add position: {e}")
            db.rollback()
            return None
        finally:
            cursor.close()
    
    @classmethod
    def close_position(cls, position_id: int, close_price: float, realized_pnl: float) -> bool:
        """
        Close a position
        
        Args:
            position_id: Position ID
            close_price: Closing price
            realized_pnl: Realized P&L
            
        Returns:
            Success status
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                UPDATE {cls.TABLE_NAME} SET
                    status = 'closed',
                    close_price = %s,
                    close_time = NOW(),
                    realized_pnl = %s
                WHERE id = %s
            """, (close_price, realized_pnl, position_id))
            
            db.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            db.rollback()
            return False
        finally:
            cursor.close()
    
    @classmethod
    def get_position_by_id(cls, position_id: int) -> Optional[Dict[str, Any]]:
        """
        Get position by ID
        
        Args:
            position_id: Position ID
            
        Returns:
            Position dict or None
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"SELECT * FROM {cls.TABLE_NAME} WHERE id = %s", (position_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return None
        finally:
            cursor.close()


# ==================== Trade Model ====================

class FuturesTrade:
    """
    Futures Trade Record Model
    期货交易记录模型
    """
    
    TABLE_NAME = "qd_futures_trades"
    
    @classmethod
    def get_db(cls):
        """Get database connection"""
        return get_db_connection()
    
    @classmethod
    def get_trades(
        cls,
        user_id: int = 1,
        limit: int = 50,
        offset: int = 0,
        symbol: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade records
        
        Args:
            user_id: User ID
            limit: Number of records
            offset: Offset for pagination
            symbol: Filter by symbol (optional)
            
        Returns:
            List of trades
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            
            if symbol:
                cursor.execute(f"""
                    SELECT * FROM {cls.TABLE_NAME}
                    WHERE user_id = %s AND symbol = %s
                    ORDER BY trade_time DESC
                    LIMIT %s OFFSET %s
                """, (user_id, symbol, limit, offset))
            else:
                cursor.execute(f"""
                    SELECT * FROM {cls.TABLE_NAME}
                    WHERE user_id = %s
                    ORDER BY trade_time DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))
            
            rows = cursor.fetchall()
            if not rows:
                return []
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []
        finally:
            cursor.close()
    
    @classmethod
    def add_trade(cls, user_id: int, trade: Dict[str, Any]) -> Optional[int]:
        """
        Add a new trade record
        
        Args:
            user_id: User ID
            trade: Trade data
            
        Returns:
            Trade ID or None
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                INSERT INTO {cls.TABLE_NAME}
                (user_id, symbol, trade_type, price, quantity, margin, fee, pnl, signal_reason, trade_time, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                user_id,
                trade.get('symbol'),
                trade.get('trade_type'),
                trade.get('price'),
                trade.get('quantity', 1),
                trade.get('margin', 0),
                trade.get('fee', 0),
                trade.get('pnl', 0),
                trade.get('signal_reason', ''),
                trade.get('trade_time', datetime.now())
            ))
            
            result = cursor.fetchone()
            db.commit()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to add trade: {e}")
            db.rollback()
            return None
        finally:
            cursor.close()
    
    @classmethod
    def get_pnl_summary(cls, user_id: int = 1, period: str = 'month') -> Dict[str, Any]:
        """
        Get P&L summary
        
        Args:
            user_id: User ID
            period: Time period (day/week/month/year)
            
        Returns:
            P&L summary dict
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            
            # Calculate date range
            if period == 'day':
                date_filter = "trade_time >= CURRENT_DATE"
            elif period == 'week':
                date_filter = "trade_time >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == 'month':
                date_filter = "trade_time >= CURRENT_DATE - INTERVAL '30 days'"
            elif period == 'year':
                date_filter = "trade_time >= CURRENT_DATE - INTERVAL '365 days'"
            else:
                date_filter = "1=1"
            
            # Get summary
            cursor.execute(f"""
                SELECT
                    COALESCE(SUM(pnl), 0) as total_pnl,
                    COALESCE(SUM(fee), 0) as total_fee,
                    COUNT(*) as trade_count,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as win_count,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as loss_count
                FROM {cls.TABLE_NAME}
                WHERE user_id = %s AND {date_filter}
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                total_pnl, total_fee, trade_count, win_count, loss_count = row
                win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
                
                return {
                    'total_pnl': float(total_pnl or 0),
                    'total_fee': float(total_fee or 0),
                    'net_pnl': float((total_pnl or 0) - (total_fee or 0)),
                    'trade_count': trade_count or 0,
                    'win_count': win_count or 0,
                    'loss_count': loss_count or 0,
                    'win_rate': round(win_rate, 2),
                    'period': period
                }
            
            return {
                'total_pnl': 0,
                'total_fee': 0,
                'net_pnl': 0,
                'trade_count': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'period': period
            }
            
        except Exception as e:
            logger.error(f"Failed to get pnl summary: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()
    
    @classmethod
    def get_pnl_history(cls, user_id: int = 1, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily P&L history
        
        Args:
            user_id: User ID
            days: Number of days
            
        Returns:
            List of daily P&L records
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                SELECT
                    DATE(trade_time) as date,
                    SUM(pnl) as daily_pnl,
                    SUM(fee) as daily_fee,
                    COUNT(*) as trade_count
                FROM {cls.TABLE_NAME}
                WHERE user_id = %s AND trade_time >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(trade_time)
                ORDER BY date ASC
            """, (user_id, days))
            
            rows = cursor.fetchall()
            if not rows:
                return []
            
            result = []
            cumulative_pnl = 0
            for row in rows:
                date, daily_pnl, daily_fee, trade_count = row
                cumulative_pnl += float(daily_pnl or 0)
                result.append({
                    'date': str(date),
                    'daily_pnl': float(daily_pnl or 0),
                    'daily_fee': float(daily_fee or 0),
                    'trade_count': trade_count or 0,
                    'cumulative_pnl': cumulative_pnl
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get pnl history: {e}")
            return []
        finally:
            cursor.close()


# ==================== Signal Model ====================

class FuturesSignal:
    """
    Futures Signal Record Model
    期货信号记录模型
    """
    
    TABLE_NAME = "qd_futures_signals"
    
    @classmethod
    def get_db(cls):
        """Get database connection"""
        return get_db_connection()
    
    @classmethod
    def get_signals(
        cls,
        user_id: int = 1,
        limit: int = 50,
        symbol: str = None,
        executed: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Get signal records
        
        Args:
            user_id: User ID
            limit: Number of records
            symbol: Filter by symbol
            executed: Filter by execution status
            
        Returns:
            List of signals
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            
            query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s"
            params = [user_id]
            
            if symbol:
                query += " AND symbol = %s"
                params.append(symbol)
            
            if executed is not None:
                query += " AND is_executed = %s"
                params.append(executed)
            
            query += " ORDER BY signal_time DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            if not rows:
                return []
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get signals: {e}")
            return []
        finally:
            cursor.close()
    
    @classmethod
    def add_signal(cls, user_id: int, signal: Dict[str, Any]) -> Optional[int]:
        """
        Add a new signal record
        
        Args:
            user_id: User ID
            signal: Signal data
            
        Returns:
            Signal ID or None
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                INSERT INTO {cls.TABLE_NAME}
                (user_id, symbol, signal_type, trigger_price, base_price, drop_pct, is_executed, signal_time, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                user_id,
                signal.get('symbol'),
                signal.get('signal_type'),
                signal.get('trigger_price'),
                signal.get('base_price'),
                signal.get('drop_pct'),
                signal.get('is_executed', False),
                signal.get('signal_time', datetime.now())
            ))
            
            result = cursor.fetchone()
            db.commit()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to add signal: {e}")
            db.rollback()
            return None
        finally:
            cursor.close()
    
    @classmethod
    def mark_executed(cls, signal_id: int) -> bool:
        """
        Mark a signal as executed
        
        Args:
            signal_id: Signal ID
            
        Returns:
            Success status
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                f"UPDATE {cls.TABLE_NAME} SET is_executed = TRUE WHERE id = %s",
                (signal_id,)
            )
            db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark signal executed: {e}")
            db.rollback()
            return False
        finally:
            cursor.close()
    
    @classmethod
    def get_today_signal_count(cls, user_id: int = 1) -> int:
        """
        Get today's signal count
        
        Args:
            user_id: User ID
            
        Returns:
            Signal count
        """
        db = cls.get_db()
        try:
            cursor = db.cursor()
            cursor.execute(f"""
                SELECT COUNT(*) FROM {cls.TABLE_NAME}
                WHERE user_id = %s AND DATE(signal_time) = CURRENT_DATE
            """, (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get signal count: {e}")
            return 0
        finally:
            cursor.close()


# ==================== Database Migration ====================

def create_futures_tables():
    """
    Create futures tables if they don't exist
    创建期货相关表（如果不存在）
    """
    db = get_db_connection()
    
    try:
        cursor = db.cursor()
        
        # Create strategy config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qd_futures_strategy_config (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                symbols TEXT DEFAULT '["IC0","IM0","IF0","IH0"]',
                drop_threshold_1 DECIMAL(10,4) DEFAULT -2.0,
                drop_threshold_2 DECIMAL(10,4) DEFAULT -3.0,
                monitoring_start VARCHAR(10) DEFAULT '09:30',
                monitoring_end VARCHAR(10) DEFAULT '15:00',
                max_position INTEGER DEFAULT 1,
                notification_channels TEXT DEFAULT '["browser"]',
                telegram_chat_id VARCHAR(100) DEFAULT '',
                wechat_webhook VARCHAR(500) DEFAULT '',
                is_running BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create index for user_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_config_user_id
            ON qd_futures_strategy_config(user_id)
        """)
        
        # Create positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qd_futures_positions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) DEFAULT 'long',
                quantity INTEGER DEFAULT 1,
                entry_price DECIMAL(20,4) NOT NULL,
                entry_time TIMESTAMP DEFAULT NOW(),
                status VARCHAR(20) DEFAULT 'open',
                close_price DECIMAL(20,4),
                close_time TIMESTAMP,
                realized_pnl DECIMAL(20,4) DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_positions_user_id
            ON qd_futures_positions(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_positions_status
            ON qd_futures_positions(status)
        """)
        
        # Create trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qd_futures_trades (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                symbol VARCHAR(20) NOT NULL,
                trade_type VARCHAR(20) NOT NULL,
                price DECIMAL(20,4) NOT NULL,
                quantity INTEGER DEFAULT 1,
                margin DECIMAL(20,4) DEFAULT 0,
                fee DECIMAL(20,4) DEFAULT 0,
                pnl DECIMAL(20,4) DEFAULT 0,
                signal_reason TEXT DEFAULT '',
                trade_time TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_trades_user_id
            ON qd_futures_trades(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_trades_trade_time
            ON qd_futures_trades(trade_time)
        """)
        
        # Create signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qd_futures_signals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                symbol VARCHAR(20) NOT NULL,
                signal_type VARCHAR(30) NOT NULL,
                trigger_price DECIMAL(20,4) NOT NULL,
                base_price DECIMAL(20,4),
                drop_pct DECIMAL(10,4),
                is_executed BOOLEAN DEFAULT FALSE,
                signal_time TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_signals_user_id
            ON qd_futures_signals(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_signals_signal_time
            ON qd_futures_signals(signal_time)
        """)
        
        db.commit()
        logger.info("Futures tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create futures tables: {e}")
        db.rollback()
        return False
    finally:
        cursor.close()


def insert_default_config(user_id: int = 1):
    """
    Insert default strategy configuration
    插入默认策略配置
    
    Args:
        user_id: User ID
    """
    config = FuturesStrategyConfig.get_config(user_id)
    if not config:
        default_config = {
            'symbols': ['IC0', 'IM0', 'IF0', 'IH0'],
            'drop_threshold_1': -2.0,
            'drop_threshold_2': -3.0,
            'monitoring_start': '09:30',
            'monitoring_end': '15:00',
            'max_position': 1,
            'notification_channels': ['browser'],
            'telegram_chat_id': '',
            'wechat_webhook': ''
        }
        FuturesStrategyConfig.save_config(user_id, default_config)
        logger.info(f"Default futures config created for user {user_id}")


# Auto-create tables on module import
try:
    create_futures_tables()
except Exception as e:
    logger.warning(f"Could not auto-create futures tables: {e}")
