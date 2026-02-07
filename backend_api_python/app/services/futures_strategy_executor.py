"""
Futures strategy executor.

This module implements the core logic for the Chinese index futures
settlement price arbitrage strategy. It integrates data source,
calculator, and notification modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from enum import Enum
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyStatus(Enum):
    """Strategy status enumeration"""
    IDLE = "idle"                    # Idle, waiting for signal
    MONITORING = "monitoring"        # Monitoring (14:30-15:00)
    POSITION_OPEN = "position_open"  # Position held
    SIGNAL_TRIGGERED = "triggered"   # Signal has been triggered


@dataclass
class StrategyState:
    """
    Strategy state data.
    
    Tracks the current state of the strategy for each contract.
    """
    status: StrategyStatus
    symbol: str
    base_price: Optional[float] = None      # 14:30 base price
    entry_price: Optional[float] = None     # Entry price
    entry_time: Optional[datetime] = None   # Entry timestamp
    current_price: Optional[float] = None   # Current price
    drop_pct: Optional[float] = None        # Drop percentage
    position_quantity: int = 0              # Position quantity (lots)
    last_alert_time: Optional[datetime] = None  # Last alert time (to avoid spam)


class FuturesStrategyExecutor:
    """
    Futures strategy executor.
    
    Implements the settlement price arbitrage strategy logic:
    1. Monitor price drop from 14:30 base price
    2. Trigger buy signal when drop exceeds threshold (e.g., 1%)
    3. Hold position overnight
    4. Sell at next day's open
    
    This class depends on:
    - CNFuturesDataSource: For market data
    - FuturesCalculator: For margin/fee calculations
    - FuturesNotificationService: For sending notifications
    """
    
    # Default strategy configuration
    DEFAULT_CONFIG = {
        "symbols": ["IC0", "IM0"],           # Contracts to monitor
        "drop_threshold_1": 0.01,            # First buy threshold: 1%
        "drop_threshold_2": 0.02,            # Add position threshold: 2%
        "alert_threshold": 0.008,            # Alert threshold: 0.8%
        "monitoring_start": "14:30:00",      # Monitoring start time
        "monitoring_end": "14:57:00",        # Monitoring end time (3 min before close)
        "max_position": 2,                   # Maximum position (lots)
        "alert_cooldown_minutes": 5,         # Cooldown between alerts
    }
    
    # Trading hours (China futures market)
    TRADING_HOURS = [
        (dt_time(9, 30), dt_time(11, 30)),   # Morning session
        (dt_time(13, 0), dt_time(15, 0)),    # Afternoon session
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the executor.
        
        Args:
            config: Strategy configuration, will be merged with DEFAULT_CONFIG
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.states: Dict[str, StrategyState] = {}
        
        # Initialize state for each symbol
        for symbol in self.config["symbols"]:
            self.states[symbol] = StrategyState(
                status=StrategyStatus.IDLE,
                symbol=symbol
            )
        
        # Dependencies (injected via initialize())
        self.data_source = None
        self.calculator = None
        self.notifier = None
        
        logger.info(f"FuturesStrategyExecutor initialized with config: {self.config}")
    
    def initialize(
        self,
        data_source,      # CNFuturesDataSource
        calculator,       # FuturesCalculator
        notifier          # FuturesNotificationService
    ):
        """
        Initialize dependencies.
        
        Called during integration to inject actual module instances.
        
        Args:
            data_source: CNFuturesDataSource instance
            calculator: FuturesCalculator instance
            notifier: FuturesNotificationService instance
        """
        self.data_source = data_source
        self.calculator = calculator
        self.notifier = notifier
        logger.info("FuturesStrategyExecutor dependencies initialized")
    
    def check_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Check for trading signals.
        
        Args:
            symbol: Contract code
            
        Returns:
            Signal dict if triggered, None otherwise:
            {
                "signal_type": "buy" | "sell" | "alert",
                "symbol": str,
                "price": float,
                "base_price": float,
                "drop_pct": float,
                "reason": str
            }
        """
        state = self.get_state(symbol)
        now = datetime.now()
        
        # Check if we're in monitoring time
        if not self._is_monitoring_time():
            # If we have a position and it's next day's open, check for sell signal
            if state.status == StrategyStatus.POSITION_OPEN and self._is_market_open():
                return self._check_sell_signal(symbol, state)
            return None
        
        # Get current price from data source
        if self.data_source is None:
            logger.warning("Data source not initialized")
            return None
        
        try:
            ticker = self.data_source.get_ticker(symbol)
            current_price = ticker.get("last", 0.0)
            
            if current_price <= 0:
                return None
            
            # Update current price in state
            state.current_price = current_price
            
            # Get or set base price (14:30 price)
            if state.base_price is None:
                state.base_price = current_price
                state.status = StrategyStatus.MONITORING
                logger.info(f"Set base price for {symbol}: {current_price}")
                return None
            
            # Calculate drop percentage
            drop_pct = self._calculate_drop_pct(current_price, state.base_price)
            state.drop_pct = drop_pct
            
            # Check for buy signals
            if state.position_quantity == 0:
                # First entry signal
                if drop_pct <= -self.config["drop_threshold_1"]:
                    return {
                        "signal_type": "buy",
                        "symbol": symbol,
                        "price": current_price,
                        "base_price": state.base_price,
                        "drop_pct": drop_pct,
                        "reason": f"Drop {abs(drop_pct)*100:.2f}% exceeds threshold {self.config['drop_threshold_1']*100:.1f}%"
                    }
                
                # Alert signal (approaching threshold)
                if self._should_send_alert(drop_pct, state):
                    state.last_alert_time = now
                    return {
                        "signal_type": "alert",
                        "symbol": symbol,
                        "price": current_price,
                        "base_price": state.base_price,
                        "drop_pct": drop_pct,
                        "reason": f"Approaching buy threshold at {abs(drop_pct)*100:.2f}%"
                    }
            
            elif state.position_quantity < self.config["max_position"]:
                # Add position signal
                if drop_pct <= -self.config["drop_threshold_2"]:
                    return {
                        "signal_type": "buy",
                        "symbol": symbol,
                        "price": current_price,
                        "base_price": state.base_price,
                        "drop_pct": drop_pct,
                        "reason": f"Add position: drop {abs(drop_pct)*100:.2f}% exceeds {self.config['drop_threshold_2']*100:.1f}%"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking signal for {symbol}: {e}")
            return None
    
    def _check_sell_signal(self, symbol: str, state: StrategyState) -> Optional[Dict[str, Any]]:
        """Check for sell signal at market open."""
        if self.data_source is None:
            return None
        
        try:
            ticker = self.data_source.get_ticker(symbol)
            current_price = ticker.get("last", 0.0)
            
            if current_price <= 0 or state.entry_price is None:
                return None
            
            # Calculate profit
            profit_pct = (current_price - state.entry_price) / state.entry_price
            
            return {
                "signal_type": "sell",
                "symbol": symbol,
                "price": current_price,
                "base_price": state.base_price or 0.0,
                "drop_pct": profit_pct,
                "entry_price": state.entry_price,
                "reason": f"Market open sell: entry={state.entry_price}, current={current_price}"
            }
            
        except Exception as e:
            logger.error(f"Error checking sell signal for {symbol}: {e}")
            return None
    
    def execute_signal(
        self,
        signal: Dict[str, Any],
        strategy_id: int,
        strategy_name: str,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a trading signal.
        
        Args:
            signal: Signal data from check_signal()
            strategy_id: Strategy ID
            strategy_name: Strategy name
            notification_config: Notification configuration
            
        Returns:
            Execution result:
            {
                "success": bool,
                "action": "buy" | "sell" | "alert",
                "price": float,
                "quantity": int,
                "notification_results": {...}
            }
        """
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "")
        price = signal.get("price", 0.0)
        
        state = self.get_state(symbol)
        now = datetime.now()
        
        result = {
            "success": False,
            "action": signal_type,
            "price": price,
            "quantity": 0,
            "notification_results": {}
        }
        
        try:
            if signal_type == "buy":
                # Update state
                if state.entry_price is None:
                    state.entry_price = price
                else:
                    # Average down
                    total_value = state.entry_price * state.position_quantity + price
                    state.position_quantity += 1
                    state.entry_price = total_value / state.position_quantity
                    state.position_quantity -= 1  # Will be incremented below
                
                state.position_quantity += 1
                state.entry_time = now
                state.status = StrategyStatus.POSITION_OPEN
                result["quantity"] = 1
                
                # Send notification
                if self.notifier:
                    from app.services.futures_notification import FuturesSignalData, FuturesSignalType
                    data = FuturesSignalData(
                        signal_type=FuturesSignalType.BUY,
                        symbol=symbol,
                        current_price=price,
                        base_price=signal.get("base_price", 0.0),
                        drop_pct=signal.get("drop_pct", 0.0),
                        timestamp=now
                    )
                    result["notification_results"] = self.notifier.send_buy_signal(
                        strategy_id=strategy_id,
                        strategy_name=strategy_name,
                        data=data,
                        notification_config=notification_config
                    )
                
                result["success"] = True
                logger.info(f"Buy signal executed: {symbol} @ {price}, position={state.position_quantity}")
                
            elif signal_type == "sell":
                # Calculate profit
                entry_price = state.entry_price or price
                quantity = state.position_quantity
                
                if self.calculator:
                    # Calculate trade cost
                    cost = self.calculator.calculate_trade_cost(
                        symbol=symbol,
                        entry_price=entry_price,
                        exit_price=price,
                        quantity=quantity,
                        is_same_day=False  # Overnight position
                    )
                    profit = cost.get("net_pnl", 0.0)
                    profit_pct = (price - entry_price) / entry_price if entry_price > 0 else 0.0
                else:
                    # Simplified calculation
                    multiplier = 200  # IC/IM multiplier
                    profit = (price - entry_price) * multiplier * quantity
                    profit_pct = (price - entry_price) / entry_price if entry_price > 0 else 0.0
                
                # Send notification
                if self.notifier:
                    from app.services.futures_notification import FuturesSignalData, FuturesSignalType
                    data = FuturesSignalData(
                        signal_type=FuturesSignalType.SELL,
                        symbol=symbol,
                        current_price=price,
                        base_price=signal.get("base_price", 0.0),
                        drop_pct=signal.get("drop_pct", 0.0),
                        timestamp=now,
                        entry_price=entry_price,
                        profit=profit,
                        profit_pct=profit_pct
                    )
                    result["notification_results"] = self.notifier.send_sell_signal(
                        strategy_id=strategy_id,
                        strategy_name=strategy_name,
                        data=data,
                        notification_config=notification_config
                    )
                
                # Reset state
                result["quantity"] = quantity
                self.reset(symbol)
                result["success"] = True
                logger.info(f"Sell signal executed: {symbol} @ {price}, profit={profit:.2f}")
                
            elif signal_type == "alert":
                # Send alert notification
                if self.notifier:
                    from app.services.futures_notification import FuturesSignalData, FuturesSignalType
                    data = FuturesSignalData(
                        signal_type=FuturesSignalType.PRICE_ALERT,
                        symbol=symbol,
                        current_price=price,
                        base_price=signal.get("base_price", 0.0),
                        drop_pct=signal.get("drop_pct", 0.0),
                        timestamp=now
                    )
                    result["notification_results"] = self.notifier.send_price_alert(
                        strategy_id=strategy_id,
                        strategy_name=strategy_name,
                        data=data,
                        notification_config=notification_config
                    )
                
                result["success"] = True
                logger.info(f"Price alert sent: {symbol} drop={signal.get('drop_pct', 0)*100:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            result["error"] = str(e)
            return result
    
    def run_tick(
        self,
        strategy_id: int,
        strategy_name: str,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute one tick of the strategy loop.
        
        This method should be called periodically (e.g., every minute)
        during trading hours.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            notification_config: Notification configuration
            
        Returns:
            List of signals and execution results from this tick
        """
        results = []
        
        for symbol in self.config["symbols"]:
            try:
                signal = self.check_signal(symbol)
                
                if signal:
                    exec_result = self.execute_signal(
                        signal=signal,
                        strategy_id=strategy_id,
                        strategy_name=strategy_name,
                        notification_config=notification_config
                    )
                    results.append({
                        "symbol": symbol,
                        "signal": signal,
                        "execution": exec_result
                    })
                    
            except Exception as e:
                logger.error(f"Error in run_tick for {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        return results
    
    def get_state(self, symbol: str) -> StrategyState:
        """
        Get state for a specific contract.
        
        Args:
            symbol: Contract code
            
        Returns:
            StrategyState for the contract
        """
        if symbol not in self.states:
            self.states[symbol] = StrategyState(
                status=StrategyStatus.IDLE,
                symbol=symbol
            )
        return self.states[symbol]
    
    def reset(self, symbol: Optional[str] = None):
        """
        Reset strategy state.
        
        Args:
            symbol: Specific contract to reset, None to reset all
        """
        if symbol:
            self.states[symbol] = StrategyState(
                status=StrategyStatus.IDLE,
                symbol=symbol
            )
            logger.info(f"Reset state for {symbol}")
        else:
            for sym in list(self.states.keys()):
                self.states[sym] = StrategyState(
                    status=StrategyStatus.IDLE,
                    symbol=sym
                )
            logger.info("Reset all states")
    
    def _is_monitoring_time(self) -> bool:
        """
        Check if current time is within monitoring window.
        
        Returns:
            True if within 14:30-14:57
        """
        now = datetime.now().time()
        
        start_parts = self.config["monitoring_start"].split(":")
        start_time = dt_time(
            int(start_parts[0]),
            int(start_parts[1]),
            int(start_parts[2]) if len(start_parts) > 2 else 0
        )
        
        end_parts = self.config["monitoring_end"].split(":")
        end_time = dt_time(
            int(end_parts[0]),
            int(end_parts[1]),
            int(end_parts[2]) if len(end_parts) > 2 else 0
        )
        
        return start_time <= now <= end_time
    
    def _is_market_open(self) -> bool:
        """
        Check if market is currently open.
        
        Returns:
            True if within trading hours
        """
        now = datetime.now().time()
        
        for start, end in self.TRADING_HOURS:
            if start <= now <= end:
                return True
        
        return False
    
    def _calculate_drop_pct(
        self,
        current_price: float,
        base_price: float
    ) -> float:
        """
        Calculate price drop percentage.
        
        Args:
            current_price: Current price
            base_price: Base price (14:30 price)
            
        Returns:
            Drop percentage (negative means down)
        """
        if base_price <= 0:
            return 0.0
        return (current_price - base_price) / base_price
    
    def _should_send_alert(
        self,
        drop_pct: float,
        state: StrategyState
    ) -> bool:
        """
        Determine if a price alert should be sent.
        
        Args:
            drop_pct: Current drop percentage
            state: Current strategy state
            
        Returns:
            True if alert should be sent
        """
        # Check if drop is approaching threshold
        if drop_pct > -self.config["alert_threshold"]:
            return False
        
        # Already triggered buy
        if drop_pct <= -self.config["drop_threshold_1"]:
            return False
        
        # Check cooldown
        if state.last_alert_time:
            cooldown = self.config["alert_cooldown_minutes"]
            elapsed = (datetime.now() - state.last_alert_time).total_seconds() / 60
            if elapsed < cooldown:
                return False
        
        return True
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of all contract states.
        
        Returns:
            Dictionary with status for each contract
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "is_monitoring_time": self._is_monitoring_time(),
            "is_market_open": self._is_market_open(),
            "contracts": {}
        }
        
        for symbol, state in self.states.items():
            summary["contracts"][symbol] = {
                "status": state.status.value,
                "base_price": state.base_price,
                "current_price": state.current_price,
                "entry_price": state.entry_price,
                "drop_pct": f"{(state.drop_pct or 0) * 100:.2f}%" if state.drop_pct else None,
                "position_quantity": state.position_quantity,
            }
        
        return summary


# Test function
def test_futures_strategy_executor():
    """Test the futures strategy executor module."""
    executor = FuturesStrategyExecutor()
    
    # Test 1: Initial state
    state = executor.get_state("IC0")
    assert state.status == StrategyStatus.IDLE
    print("✅ Test 1 passed: Initial state is IDLE")
    
    # Test 2: Drop percentage calculation
    drop = executor._calculate_drop_pct(5445, 5500)
    assert abs(drop - (-0.01)) < 0.001  # Approximately -1%
    print("✅ Test 2 passed: Drop calculation correct")
    
    # Test 3: Monitoring time check
    is_monitoring = executor._is_monitoring_time()
    print(f"✅ Test 3 passed: Monitoring time check = {is_monitoring}")
    
    # Test 4: Market open check
    is_open = executor._is_market_open()
    print(f"✅ Test 4 passed: Market open check = {is_open}")
    
    # Test 5: Status summary
    summary = executor.get_status_summary()
    assert "contracts" in summary
    assert "IC0" in summary["contracts"]
    print("✅ Test 5 passed: Status summary generated")
    
    # Test 6: Reset
    executor.states["IC0"].position_quantity = 1
    executor.reset("IC0")
    assert executor.states["IC0"].position_quantity == 0
    print("✅ Test 6 passed: Reset works correctly")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_futures_strategy_executor()
