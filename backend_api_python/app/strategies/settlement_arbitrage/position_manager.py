# Settlement Arbitrage Strategy - Position Manager
# 结算价差套利策略 - 仓位管理

"""
Manages positions for the Settlement Arbitrage Strategy.

Tracks open/close positions, calculates P&L, and provides
position persistence via in-memory storage (with optional DB support).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.data_sources.cn_futures import CNFuturesDataSource
from app.strategies.settlement_arbitrage.config import StrategyConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PositionDirection(Enum):
    """Position direction."""
    LONG = "long"
    SHORT = "short"


class PositionStatus(Enum):
    """Position lifecycle status."""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class Position:
    """
    Represents a single position.
    
    Attributes:
        id: Unique position identifier
        symbol: Contract code
        direction: LONG or SHORT
        quantity: Number of lots
        entry_price: Entry price
        entry_time: Entry timestamp
        level: Entry level (1=first, 2=additional)
        base_price: 14:30 base price when signal triggered
        drop_pct: Drop percentage at entry
        vwap: VWAP at entry time
        exit_price: Exit price (None if still open)
        exit_time: Exit timestamp (None if still open)
        status: OPEN or CLOSED
        pnl: Realized P&L (set when closed)
        fee: Transaction fees
    """
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    symbol: str = ""
    direction: PositionDirection = PositionDirection.LONG
    quantity: int = 1
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    level: int = 1
    base_price: float = 0.0
    drop_pct: float = 0.0
    vwap: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: PositionStatus = PositionStatus.OPEN
    pnl: float = 0.0
    fee: float = 0.0
    margin: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'level': self.level,
            'base_price': self.base_price,
            'drop_pct': self.drop_pct,
            'vwap': self.vwap,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'status': self.status.value,
            'pnl': self.pnl,
            'fee': self.fee,
            'margin': self.margin,
        }


@dataclass
class TradeRecord:
    """
    A completed trade (entry + exit).
    
    Attributes:
        position: The closed position
        gross_pnl: P&L before fees
        net_pnl: P&L after fees
        holding_hours: Duration of hold in hours
    """
    position: Position
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    holding_hours: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = self.position.to_dict()
        d.update({
            'gross_pnl': self.gross_pnl,
            'net_pnl': self.net_pnl,
            'holding_hours': self.holding_hours,
        })
        return d


class PositionManager:
    """
    Manages positions for the Settlement Arbitrage Strategy.
    
    Provides:
    - Open/close position tracking
    - P&L calculation (including fees and multiplier)
    - Position limits enforcement
    - Trade history recording
    
    Usage:
        pm = PositionManager(config)
        pos = pm.open_position("IM0", price=5826.4, quantity=1, level=1)
        trades = pm.close_all_positions(exit_price=5890.0)
    """
    
    # Default fee rates per contract
    DEFAULT_FEE_RATES = {
        'IC': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IM': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IF': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IH': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
    }
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        
        # Open positions: {position_id: Position}
        self._open_positions: Dict[str, Position] = {}
        
        # Closed positions (trade history)
        self._trade_history: List[TradeRecord] = []
        
        # Product info cache
        self._product_info = CNFuturesDataSource.PRODUCTS
    
    def open_position(
        self,
        symbol: str,
        price: float,
        quantity: int,
        level: int = 1,
        base_price: float = 0.0,
        drop_pct: float = 0.0,
        vwap: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Position:
        """
        Open a new position.
        
        Args:
            symbol: Contract code (e.g., "IM0")
            price: Entry price
            quantity: Number of lots
            level: Entry level (1=first, 2=additional)
            base_price: 14:30 base price
            drop_pct: Drop percentage at entry
            vwap: Current VWAP
            timestamp: Entry timestamp
            
        Returns:
            New Position object
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calculate margin
        product = symbol[:2].upper()
        info = self._product_info.get(product, {})
        multiplier = info.get('multiplier', 200)
        margin_ratio = info.get('margin_ratio', 0.12)
        margin = price * multiplier * quantity * margin_ratio
        
        position = Position(
            symbol=symbol,
            direction=PositionDirection.LONG,
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            level=level,
            base_price=base_price,
            drop_pct=drop_pct,
            vwap=vwap,
            margin=margin,
        )
        
        self._open_positions[position.id] = position
        
        logger.info(
            f"Position opened: {position.id} {symbol} L{level} "
            f"qty={quantity} price={price} margin={margin:.0f}"
        )
        
        return position
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        timestamp: Optional[datetime] = None
    ) -> Optional[TradeRecord]:
        """
        Close a specific position.
        
        Args:
            position_id: Position ID to close
            exit_price: Exit price
            timestamp: Exit timestamp
            
        Returns:
            TradeRecord if successful, None otherwise
        """
        position = self._open_positions.get(position_id)
        if position is None:
            logger.warning(f"Position {position_id} not found")
            return None
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calculate P&L
        product = position.symbol[:2].upper()
        info = self._product_info.get(product, {})
        multiplier = info.get('multiplier', 200)
        
        # Gross P&L = (exit - entry) * quantity * multiplier
        gross_pnl = (exit_price - position.entry_price) * position.quantity * multiplier
        
        # Calculate fees
        fee = self._calculate_fee(
            product, position.entry_price, exit_price,
            position.quantity, multiplier, is_close_today=False
        )
        
        net_pnl = gross_pnl - fee
        
        # Calculate holding time
        holding_hours = 0.0
        if position.entry_time:
            delta = timestamp - position.entry_time
            holding_hours = delta.total_seconds() / 3600
        
        # Update position
        position.exit_price = exit_price
        position.exit_time = timestamp
        position.status = PositionStatus.CLOSED
        position.pnl = net_pnl
        position.fee = fee
        
        # Move to history
        del self._open_positions[position_id]
        
        trade = TradeRecord(
            position=position,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            holding_hours=holding_hours,
        )
        self._trade_history.append(trade)
        
        logger.info(
            f"Position closed: {position_id} {position.symbol} "
            f"exit={exit_price} pnl={net_pnl:.2f} fee={fee:.2f}"
        )
        
        return trade
    
    def close_all_positions(
        self,
        exit_price: float,
        symbol: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> List[TradeRecord]:
        """
        Close all open positions (optionally filtered by symbol).
        
        Args:
            exit_price: Exit price
            symbol: Optional symbol filter
            timestamp: Exit timestamp
            
        Returns:
            List of TradeRecords
        """
        trades = []
        
        # Get positions to close
        position_ids = list(self._open_positions.keys())
        
        for pid in position_ids:
            pos = self._open_positions.get(pid)
            if pos is None:
                continue
            
            if symbol and pos.symbol != symbol:
                continue
            
            trade = self.close_position(pid, exit_price, timestamp)
            if trade:
                trades.append(trade)
        
        return trades
    
    def _calculate_fee(
        self,
        product: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        multiplier: int,
        is_close_today: bool = False
    ) -> float:
        """
        Calculate transaction fees.
        
        CFFEX index futures fees are calculated as:
        fee = price * multiplier * quantity * fee_rate
        
        Args:
            product: Product code (IC, IM, etc.)
            entry_price: Entry price
            exit_price: Exit price
            quantity: Number of lots
            multiplier: Contract multiplier
            is_close_today: Whether closing on the same day
            
        Returns:
            Total fee amount
        """
        rates = self.DEFAULT_FEE_RATES.get(product, self.DEFAULT_FEE_RATES['IM'])
        
        # Open fee
        open_fee = entry_price * multiplier * quantity * rates['open']
        
        # Close fee
        close_rate = rates['close_today'] if is_close_today else rates['close']
        close_fee = exit_price * multiplier * quantity * close_rate
        
        return round(open_fee + close_fee, 2)
    
    # ========== Query Methods ==========
    
    def get_current_positions(
        self, symbol: Optional[str] = None
    ) -> List[Position]:
        """
        Get all open positions.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open positions
        """
        positions = list(self._open_positions.values())
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        return positions
    
    def get_position_count(self, symbol: Optional[str] = None) -> int:
        """Get total open position quantity."""
        positions = self.get_current_positions(symbol)
        return sum(p.quantity for p in positions)
    
    def get_total_margin_used(self) -> float:
        """Get total margin used by all open positions."""
        return sum(p.margin for p in self._open_positions.values())
    
    def calculate_unrealized_pnl(
        self, symbol: str, current_price: float
    ) -> float:
        """
        Calculate unrealized P&L for a symbol.
        
        Args:
            symbol: Contract symbol
            current_price: Current market price
            
        Returns:
            Total unrealized P&L
        """
        total_pnl = 0.0
        product = symbol[:2].upper()
        info = self._product_info.get(product, {})
        multiplier = info.get('multiplier', 200)
        
        for pos in self._open_positions.values():
            if pos.symbol == symbol:
                pnl = (current_price - pos.entry_price) * pos.quantity * multiplier
                total_pnl += pnl
        
        return round(total_pnl, 2)
    
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TradeRecord]:
        """
        Get trade history with optional filters.
        
        Args:
            symbol: Optional symbol filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum records to return
            
        Returns:
            List of TradeRecords
        """
        trades = self._trade_history.copy()
        
        if symbol:
            trades = [t for t in trades if t.position.symbol == symbol]
        
        if start_date:
            trades = [
                t for t in trades
                if t.position.entry_time and t.position.entry_time >= start_date
            ]
        
        if end_date:
            trades = [
                t for t in trades
                if t.position.exit_time and t.position.exit_time <= end_date
            ]
        
        # Sort by exit time descending (most recent first)
        trades.sort(
            key=lambda t: t.position.exit_time or datetime.min,
            reverse=True
        )
        
        return trades[:limit]
    
    def get_pnl_summary(self) -> Dict[str, Any]:
        """
        Get P&L summary statistics.
        
        Returns:
            Dictionary with summary stats
        """
        if not self._trade_history:
            return {
                'total_trades': 0,
                'total_pnl': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_fees': 0,
            }
        
        trades = self._trade_history
        total_pnl = sum(t.net_pnl for t in trades)
        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        total_fees = sum(t.position.fee for t in trades)
        
        return {
            'total_trades': len(trades),
            'total_pnl': round(total_pnl, 2),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(len(wins) / len(trades), 4) if trades else 0,
            'avg_win': round(sum(t.net_pnl for t in wins) / len(wins), 2) if wins else 0,
            'avg_loss': round(sum(t.net_pnl for t in losses) / len(losses), 2) if losses else 0,
            'total_fees': round(total_fees, 2),
        }
    
    def has_open_positions(self, symbol: Optional[str] = None) -> bool:
        """Check if there are any open positions."""
        if symbol:
            return any(p.symbol == symbol for p in self._open_positions.values())
        return len(self._open_positions) > 0
    
    def reset(self):
        """Reset all positions and history."""
        self._open_positions.clear()
        self._trade_history.clear()
