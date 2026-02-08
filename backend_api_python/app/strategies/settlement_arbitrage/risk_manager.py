# Settlement Arbitrage Strategy - Risk Manager
# 结算价差套利策略 - 风控管理

"""
Risk management module for the Settlement Arbitrage Strategy.

Provides:
- Position limit checking
- Daily loss limit enforcement
- Maximum drawdown monitoring
- Force close mechanism
- Risk event logging
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional

from app.strategies.settlement_arbitrage.config import RiskConfig, StrategyConfig
from app.strategies.settlement_arbitrage.position_manager import PositionManager, TradeRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RiskEventType(Enum):
    """Types of risk events."""
    POSITION_LIMIT = "position_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    FORCE_CLOSE = "force_close"


@dataclass
class RiskEvent:
    """
    Represents a risk event.
    
    Attributes:
        event_type: Type of risk event
        message: Human-readable description
        value: Current value that triggered the event
        limit: The limit that was exceeded
        timestamp: When the event occurred
        action_taken: What action was taken (e.g., "force_close")
    """
    event_type: RiskEventType
    message: str
    value: float
    limit: float
    timestamp: datetime = field(default_factory=datetime.now)
    action_taken: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_type': self.event_type.value,
            'message': self.message,
            'value': self.value,
            'limit': self.limit,
            'timestamp': self.timestamp.isoformat(),
            'action_taken': self.action_taken,
        }


class RiskManager:
    """
    Risk management for the Settlement Arbitrage Strategy.
    
    Monitors and enforces:
    1. Position limits (per symbol and total)
    2. Daily loss limits
    3. Maximum drawdown
    4. Force close on limit breach
    
    Usage:
        risk_mgr = RiskManager(risk_config, strategy_config)
        
        # Before opening a position:
        event = risk_mgr.check_position_limit("IM0", position_manager)
        if event:
            # Reject the trade
            ...
        
        # After each trade:
        risk_mgr.on_trade(trade_record)
        event = risk_mgr.check_all_risks()
        if event:
            # Handle risk event (e.g., force close)
            ...
    """
    
    def __init__(
        self,
        risk_config: Optional[RiskConfig] = None,
        strategy_config: Optional[StrategyConfig] = None
    ):
        self.config = risk_config or RiskConfig()
        self.strategy_config = strategy_config or StrategyConfig()
        
        # Daily P&L tracking
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._current_date: Optional[date] = None
        
        # Drawdown tracking
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        self._initial_equity: float = 0.0
        
        # Risk event log
        self._events: List[RiskEvent] = []
        
        # Risk state
        self._is_risk_triggered: bool = False
    
    @property
    def is_risk_triggered(self) -> bool:
        """Check if any risk limit has been triggered."""
        return self._is_risk_triggered
    
    def initialize(self, initial_equity: float):
        """
        Initialize risk manager with starting equity.
        
        Args:
            initial_equity: Starting equity value
        """
        self._initial_equity = initial_equity
        self._current_equity = initial_equity
        self._peak_equity = initial_equity
        self._is_risk_triggered = False
    
    def reset_daily(self):
        """Reset daily counters. Called at start of each trading day."""
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._current_date = date.today()
        self._is_risk_triggered = False
        logger.info("RiskManager: daily counters reset")
    
    # ========== Risk Checks ==========
    
    def check_all_risks(
        self, position_manager: Optional[PositionManager] = None
    ) -> Optional[RiskEvent]:
        """
        Run all risk checks.
        
        Args:
            position_manager: Position manager for position-level checks
            
        Returns:
            RiskEvent if any limit breached, None otherwise
        """
        # Check daily loss
        event = self.check_daily_loss_limit()
        if event:
            return event
        
        # Check drawdown
        event = self.check_drawdown_limit()
        if event:
            return event
        
        return None
    
    def check_position_limit(
        self,
        symbol: str,
        position_manager: PositionManager
    ) -> Optional[RiskEvent]:
        """
        Check if opening a new position would exceed position limits.
        
        Args:
            symbol: Contract symbol
            position_manager: Position manager to query
            
        Returns:
            RiskEvent if limit would be exceeded, None otherwise
        """
        # Per-symbol limit
        symbol_qty = position_manager.get_position_count(symbol)
        max_per_symbol = self.strategy_config.max_position_per_symbol
        
        if symbol_qty >= max_per_symbol:
            event = RiskEvent(
                event_type=RiskEventType.POSITION_LIMIT,
                message=f"Position limit for {symbol}: {symbol_qty}/{max_per_symbol}",
                value=float(symbol_qty),
                limit=float(max_per_symbol),
            )
            self._events.append(event)
            logger.warning(event.message)
            return event
        
        # Total position limit
        total_qty = position_manager.get_position_count()
        max_total = self.config.max_total_position
        
        if total_qty >= max_total:
            event = RiskEvent(
                event_type=RiskEventType.POSITION_LIMIT,
                message=f"Total position limit: {total_qty}/{max_total}",
                value=float(total_qty),
                limit=float(max_total),
            )
            self._events.append(event)
            logger.warning(event.message)
            return event
        
        return None
    
    def check_daily_loss_limit(self) -> Optional[RiskEvent]:
        """
        Check if daily loss limit has been exceeded.
        
        Returns:
            RiskEvent if limit exceeded, None otherwise
        """
        if self._daily_pnl < -self.config.max_daily_loss:
            event = RiskEvent(
                event_type=RiskEventType.DAILY_LOSS_LIMIT,
                message=(
                    f"Daily loss limit exceeded: "
                    f"PnL={self._daily_pnl:.2f}, limit={-self.config.max_daily_loss:.2f}"
                ),
                value=self._daily_pnl,
                limit=-self.config.max_daily_loss,
            )
            self._is_risk_triggered = True
            self._events.append(event)
            logger.error(event.message)
            return event
        
        return None
    
    def check_drawdown_limit(self) -> Optional[RiskEvent]:
        """
        Check if maximum drawdown limit has been exceeded.
        
        Returns:
            RiskEvent if limit exceeded, None otherwise
        """
        if self._peak_equity <= 0:
            return None
        
        drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
        
        if drawdown > self.config.max_drawdown:
            event = RiskEvent(
                event_type=RiskEventType.DRAWDOWN_LIMIT,
                message=(
                    f"Drawdown limit exceeded: "
                    f"drawdown={drawdown:.2%}, limit={self.config.max_drawdown:.2%}"
                ),
                value=drawdown,
                limit=self.config.max_drawdown,
            )
            self._is_risk_triggered = True
            self._events.append(event)
            logger.error(event.message)
            return event
        
        return None
    
    # ========== Trade Event Handling ==========
    
    def on_trade(self, trade: TradeRecord):
        """
        Update risk state after a trade completes.
        
        Args:
            trade: Completed trade record
        """
        # Update daily P&L
        today = date.today()
        if self._current_date != today:
            self.reset_daily()
        
        self._daily_pnl += trade.net_pnl
        self._daily_trades += 1
        
        # Update equity tracking
        self._current_equity += trade.net_pnl
        if self._current_equity > self._peak_equity:
            self._peak_equity = self._current_equity
        
        logger.info(
            f"RiskManager: trade recorded, daily_pnl={self._daily_pnl:.2f}, "
            f"equity={self._current_equity:.2f}"
        )
    
    def force_close_all(
        self,
        position_manager: PositionManager,
        current_prices: Dict[str, float],
        reason: str = "risk_limit"
    ) -> List[TradeRecord]:
        """
        Force close all positions due to risk limit breach.
        
        Args:
            position_manager: Position manager
            current_prices: Dict of {symbol: current_price}
            reason: Reason for force close
            
        Returns:
            List of TradeRecords from forced closes
        """
        all_trades = []
        
        for symbol, price in current_prices.items():
            trades = position_manager.close_all_positions(
                exit_price=price,
                symbol=symbol,
            )
            all_trades.extend(trades)
        
        if all_trades:
            event = RiskEvent(
                event_type=RiskEventType.FORCE_CLOSE,
                message=f"Force closed {len(all_trades)} positions: {reason}",
                value=sum(t.net_pnl for t in all_trades),
                limit=0,
                action_taken="force_close",
            )
            self._events.append(event)
            logger.warning(event.message)
            
            # Update risk state
            for trade in all_trades:
                self.on_trade(trade)
        
        return all_trades
    
    # ========== Status & Reporting ==========
    
    def get_risk_status(self) -> Dict[str, Any]:
        """
        Get current risk status.
        
        Returns:
            Dictionary with risk metrics
        """
        drawdown = 0.0
        if self._peak_equity > 0:
            drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
        
        return {
            'is_risk_triggered': self._is_risk_triggered,
            'daily_pnl': round(self._daily_pnl, 2),
            'daily_trades': self._daily_trades,
            'daily_loss_limit': self.config.max_daily_loss,
            'daily_loss_remaining': round(self.config.max_daily_loss + self._daily_pnl, 2),
            'current_equity': round(self._current_equity, 2),
            'peak_equity': round(self._peak_equity, 2),
            'current_drawdown': round(drawdown, 6),
            'max_drawdown_limit': self.config.max_drawdown,
            'total_risk_events': len(self._events),
        }
    
    def get_events(
        self,
        event_type: Optional[RiskEventType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get risk event history.
        
        Args:
            event_type: Optional filter by event type
            limit: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Most recent first
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]
    
    def reset(self):
        """Full reset of risk manager."""
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._current_date = None
        self._peak_equity = 0.0
        self._current_equity = 0.0
        self._initial_equity = 0.0
        self._events = []
        self._is_risk_triggered = False
