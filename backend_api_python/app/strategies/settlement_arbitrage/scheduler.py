# Settlement Arbitrage Strategy - Scheduler
# 结算价差套利策略 - 策略调度器

"""
Strategy scheduler that orchestrates data fetching, strategy execution,
position management, risk monitoring, and notification dispatch.

This is the main entry point that ties all components together.
"""

import threading
import time as time_mod
from datetime import datetime, date, time, timedelta
from typing import Any, Callable, Dict, List, Optional

from app.data_sources.cn_futures import CNFuturesDataSource
from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig
from app.strategies.settlement_arbitrage.data_handler import MinuteDataHandler, MinuteBar
from app.strategies.settlement_arbitrage.strategy import (
    SettlementArbitrageStrategy, Signal, SignalType, StrategyState
)
from app.strategies.settlement_arbitrage.vwap_calculator import VWAPCalculator
from app.strategies.settlement_arbitrage.position_manager import PositionManager
from app.strategies.settlement_arbitrage.risk_manager import RiskManager
from app.services.futures_notification import (
    FuturesNotificationService, FuturesSignalData, FuturesSignalType
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyScheduler:
    """
    Main scheduler for the Settlement Arbitrage Strategy.
    
    Orchestrates:
    - Data handler for minute-level data
    - Strategy core for signal generation
    - Position manager for trade execution
    - Risk manager for risk control
    - Notification service for alerts
    
    Lifecycle:
    1. start() → begins background operations
    2. Automatic daily cycle:
       - 09:15 Pre-market preparation
       - 09:30-15:00 Data polling & strategy monitoring
       - 14:30-15:00 Active strategy watch period
       - 15:05 Post-market cleanup & save
    3. stop() → stops everything
    
    Usage:
        scheduler = StrategyScheduler(strategy_config, risk_config)
        scheduler.start()
        # ... runs in background ...
        scheduler.stop()
    """
    
    def __init__(
        self,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        notification_config: Optional[Dict[str, Any]] = None,
    ):
        self._config = strategy_config or StrategyConfig()
        self._risk_config = risk_config or RiskConfig()
        self._notification_config = notification_config
        
        # Core components
        self._data_source = CNFuturesDataSource()
        self._data_handler = MinuteDataHandler(data_source=self._data_source)
        self._vwap_calculator = VWAPCalculator(data_source=self._data_source)
        self._strategy = SettlementArbitrageStrategy(
            config=self._config,
            risk_config=self._risk_config,
            vwap_calculator=self._vwap_calculator,
        )
        self._position_manager = PositionManager(config=self._config)
        self._risk_manager = RiskManager(
            risk_config=self._risk_config,
            strategy_config=self._config,
        )
        self._notifier = FuturesNotificationService()
        
        # Scheduler state
        self._running = False
        self._main_thread: Optional[threading.Thread] = None
        self._started_at: Optional[datetime] = None
        self._heartbeat: Optional[datetime] = None
        
        # Strategy ID (for notification service)
        self._strategy_id = 0
        self._strategy_name = "Settlement Arbitrage"
        
        # Daily flags
        self._pre_market_done = False
        self._post_market_done = False
        self._day_open_processed: Dict[str, bool] = {}
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def strategy(self) -> SettlementArbitrageStrategy:
        return self._strategy
    
    @property
    def position_manager(self) -> PositionManager:
        return self._position_manager
    
    @property
    def risk_manager(self) -> RiskManager:
        return self._risk_manager
    
    @property
    def data_handler(self) -> MinuteDataHandler:
        return self._data_handler
    
    def start(self):
        """
        Start the strategy scheduler.
        
        Initializes all components and begins the main loop
        in a background thread.
        """
        if self._running:
            logger.warning("StrategyScheduler: already running")
            return
        
        logger.info("StrategyScheduler: starting...")
        
        # Initialize components
        self._risk_manager.initialize(initial_equity=500000.0)
        self._risk_manager.reset_daily()
        
        # Subscribe to symbols
        self._data_handler.subscribe(self._config.symbols)
        
        # Register bar callback
        self._data_handler.on_bar(self._on_minute_bar)
        
        # Start data polling
        self._data_handler.start_polling(interval=60)
        
        # Start main scheduler loop
        self._running = True
        self._started_at = datetime.now()
        self._main_thread = threading.Thread(
            target=self._main_loop,
            name="StrategyScheduler-Main",
            daemon=True,
        )
        self._main_thread.start()
        
        logger.info("StrategyScheduler: started successfully")
    
    def stop(self):
        """Stop the strategy scheduler and clean up."""
        logger.info("StrategyScheduler: stopping...")
        
        self._running = False
        
        # Stop data handler
        self._data_handler.stop()
        
        # Save data
        self._data_handler.save_all_and_cleanup()
        
        # Wait for main thread
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=10)
        
        logger.info("StrategyScheduler: stopped")
    
    def update_config(
        self,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None
    ):
        """
        Hot-update strategy configuration.
        
        Args:
            strategy_config: New strategy config
            risk_config: New risk config
        """
        if strategy_config:
            self._config = strategy_config
            self._strategy.config = strategy_config
            
            # Re-subscribe if symbols changed
            self._data_handler.subscribe(strategy_config.symbols)
            
            logger.info("StrategyScheduler: strategy config updated")
        
        if risk_config:
            self._risk_config = risk_config
            self._risk_manager.config = risk_config
            logger.info("StrategyScheduler: risk config updated")
    
    # ========== Main Loop ==========
    
    def _main_loop(self):
        """
        Main scheduler loop.
        
        Runs periodic tasks:
        - Pre-market preparation (09:15)
        - Day open position closing check (09:30)
        - Post-market cleanup (15:05)
        - Heartbeat update
        """
        while self._running:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # Update heartbeat
                self._heartbeat = now
                
                # Daily reset at midnight
                if current_time < time(0, 1):
                    self._reset_daily_flags()
                
                # Pre-market (09:15)
                if (
                    time(9, 15) <= current_time < time(9, 25)
                    and not self._pre_market_done
                ):
                    self._pre_market()
                
                # Check day open close (09:30-09:35)
                if time(9, 30) <= current_time < time(9, 35):
                    self._check_day_open_close()
                
                # Post-market (15:05)
                if (
                    time(15, 5) <= current_time < time(15, 15)
                    and not self._post_market_done
                ):
                    self._post_market()
                
            except Exception as e:
                logger.error(f"StrategyScheduler main loop error: {e}", exc_info=True)
            
            # Sleep 10 seconds between checks
            for _ in range(10):
                if not self._running:
                    return
                time_mod.sleep(1)
    
    def _on_minute_bar(self, bar: MinuteBar):
        """
        Callback for each new minute bar from data handler.
        
        This is where strategy signals are generated and processed.
        
        Args:
            bar: New minute bar data
        """
        try:
            # Feed to strategy
            signals = self._strategy.on_bar(bar)
            
            # Process generated signals
            for signal in signals:
                self._process_signal(signal, bar)
            
            # Check risk after processing
            if self._position_manager.has_open_positions():
                risk_event = self._risk_manager.check_all_risks(self._position_manager)
                if risk_event and self._risk_config.force_close_on_limit:
                    self._handle_risk_event(risk_event)
                    
        except Exception as e:
            logger.error(f"StrategyScheduler on_bar error: {e}", exc_info=True)
    
    def _process_signal(self, signal: Signal, bar: MinuteBar):
        """
        Process a trading signal.
        
        Args:
            signal: Generated signal
            bar: Current bar
        """
        if signal.signal_type == SignalType.BUY_L1:
            # Check risk limits before opening
            risk_event = self._risk_manager.check_position_limit(
                signal.symbol, self._position_manager
            )
            if risk_event:
                logger.warning(f"BUY blocked by risk: {risk_event.message}")
                return
            
            # Open position
            position = self._position_manager.open_position(
                symbol=signal.symbol,
                price=signal.price,
                quantity=signal.quantity,
                level=signal.level,
                base_price=signal.base_price,
                drop_pct=signal.drop_pct,
                vwap=signal.vwap,
                timestamp=signal.timestamp,
            )
            
            # Send notification
            self._send_signal_notification(signal)
            
        elif signal.signal_type == SignalType.BUY_L2:
            risk_event = self._risk_manager.check_position_limit(
                signal.symbol, self._position_manager
            )
            if risk_event:
                logger.warning(f"ADD blocked by risk: {risk_event.message}")
                return
            
            position = self._position_manager.open_position(
                symbol=signal.symbol,
                price=signal.price,
                quantity=signal.quantity,
                level=signal.level,
                base_price=signal.base_price,
                drop_pct=signal.drop_pct,
                vwap=signal.vwap,
                timestamp=signal.timestamp,
            )
            
            self._send_signal_notification(signal)
            
        elif signal.signal_type == SignalType.SELL_CLOSE:
            # Close all positions for this symbol
            trades = self._position_manager.close_all_positions(
                exit_price=signal.price,
                symbol=signal.symbol,
                timestamp=signal.timestamp,
            )
            
            # Update risk manager
            for trade in trades:
                self._risk_manager.on_trade(trade)
            
            # Send close notification
            if trades:
                total_pnl = sum(t.net_pnl for t in trades)
                self._send_close_notification(signal, trades, total_pnl)
            
        elif signal.signal_type == SignalType.ALERT:
            self._send_alert_notification(signal)
    
    # ========== Daily Lifecycle ==========
    
    def _pre_market(self):
        """Pre-market preparation (called around 09:15)."""
        logger.info("StrategyScheduler: pre-market preparation")
        
        # Check if today is a trading day
        if not self._data_source.is_trading_day():
            logger.info("Today is not a trading day, skipping")
            self._pre_market_done = True
            return
        
        # Reset daily state
        self._risk_manager.reset_daily()
        self._strategy.reset()  # Strategy resets for new day
        self._day_open_processed = {}
        
        # Reset VWAP calculator
        self._vwap_calculator.reset_realtime()
        
        self._pre_market_done = True
        logger.info("StrategyScheduler: pre-market done")
    
    def _check_day_open_close(self):
        """
        Check if positions from previous day need to be closed at open.
        Called around 09:30-09:35.
        """
        for symbol in self._config.symbols:
            if self._day_open_processed.get(symbol, False):
                continue
            
            if self._position_manager.has_open_positions(symbol):
                # Get opening price
                quote = self._data_source.get_realtime_quote(symbol)
                if quote and quote.get('last', 0) > 0:
                    open_price = quote['last']
                    
                    # Generate close signal via strategy
                    close_signal = self._strategy.on_day_open(
                        symbol, open_price, datetime.now()
                    )
                    
                    if close_signal:
                        self._process_signal(close_signal, None)
                    
                    self._day_open_processed[symbol] = True
                    logger.info(
                        f"Day open close: {symbol} at {open_price}"
                    )
    
    def _post_market(self):
        """Post-market cleanup (called around 15:05)."""
        logger.info("StrategyScheduler: post-market cleanup")
        
        # Save data to local storage
        self._data_handler.save_all_and_cleanup()
        
        self._post_market_done = True
        logger.info("StrategyScheduler: post-market done")
    
    def _reset_daily_flags(self):
        """Reset daily flags."""
        self._pre_market_done = False
        self._post_market_done = False
        self._day_open_processed = {}
    
    # ========== Notifications ==========
    
    def _send_signal_notification(self, signal: Signal):
        """Send buy signal notification."""
        if not self._config.notify_on_entry:
            return
        
        try:
            data = FuturesSignalData(
                signal_type=FuturesSignalType.BUY,
                symbol=signal.symbol,
                current_price=signal.price,
                base_price=signal.base_price,
                drop_pct=signal.drop_pct,
                timestamp=signal.timestamp,
            )
            
            self._notifier.send_buy_signal(
                strategy_id=self._strategy_id,
                strategy_name=self._strategy_name,
                data=data,
                notification_config=self._notification_config,
            )
        except Exception as e:
            logger.error(f"Failed to send buy notification: {e}")
    
    def _send_close_notification(
        self, signal: Signal, trades: list, total_pnl: float
    ):
        """Send close/sell notification."""
        if not self._config.notify_on_exit:
            return
        
        try:
            # Get average entry price
            avg_entry = 0.0
            total_qty = 0
            for trade in trades:
                avg_entry += trade.position.entry_price * trade.position.quantity
                total_qty += trade.position.quantity
            if total_qty > 0:
                avg_entry /= total_qty
            
            profit_pct = (signal.price - avg_entry) / avg_entry if avg_entry > 0 else 0
            
            data = FuturesSignalData(
                signal_type=FuturesSignalType.SELL,
                symbol=signal.symbol,
                current_price=signal.price,
                base_price=signal.base_price,
                drop_pct=signal.drop_pct,
                timestamp=signal.timestamp,
                entry_price=avg_entry,
                profit=total_pnl,
                profit_pct=profit_pct,
            )
            
            self._notifier.send_sell_signal(
                strategy_id=self._strategy_id,
                strategy_name=self._strategy_name,
                data=data,
                notification_config=self._notification_config,
            )
        except Exception as e:
            logger.error(f"Failed to send close notification: {e}")
    
    def _send_alert_notification(self, signal: Signal):
        """Send price alert notification."""
        if not self._config.notify_on_alert:
            return
        
        try:
            data = FuturesSignalData(
                signal_type=FuturesSignalType.PRICE_ALERT,
                symbol=signal.symbol,
                current_price=signal.price,
                base_price=signal.base_price,
                drop_pct=signal.drop_pct,
                timestamp=signal.timestamp,
            )
            
            self._notifier.send_price_alert(
                strategy_id=self._strategy_id,
                strategy_name=self._strategy_name,
                data=data,
                notification_config=self._notification_config,
            )
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def _handle_risk_event(self, risk_event):
        """Handle a risk limit breach by force closing positions."""
        logger.warning(f"Risk event triggered: {risk_event.message}")
        
        # Get current prices for all symbols
        current_prices = {}
        for symbol in self._config.symbols:
            quote = self._data_source.get_realtime_quote(symbol)
            if quote and quote.get('last', 0) > 0:
                current_prices[symbol] = quote['last']
        
        # Force close
        trades = self._risk_manager.force_close_all(
            self._position_manager, current_prices, risk_event.message
        )
        
        logger.warning(
            f"Force closed {len(trades)} positions, "
            f"total pnl={sum(t.net_pnl for t in trades):.2f}"
        )
    
    # ========== Status ==========
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status.
        
        Returns:
            Dictionary with all status information
        """
        return {
            'is_running': self._running,
            'started_at': self._started_at.isoformat() if self._started_at else None,
            'heartbeat': self._heartbeat.isoformat() if self._heartbeat else None,
            'config': {
                'symbols': self._config.symbols,
                'threshold_1': self._config.threshold_1,
                'threshold_2': self._config.threshold_2,
                'alert_threshold': self._config.alert_threshold,
            },
            'strategy': self._strategy.get_monitor_data(),
            'positions': {
                'open_count': self._position_manager.get_position_count(),
                'open_positions': [
                    p.to_dict() for p in self._position_manager.get_current_positions()
                ],
                'margin_used': self._position_manager.get_total_margin_used(),
            },
            'risk': self._risk_manager.get_risk_status(),
            'pnl_summary': self._position_manager.get_pnl_summary(),
            'is_trading_time': self._data_source.is_trading_time(),
            'is_watch_period': self._data_source.is_watch_period(),
        }


# Global scheduler instance (singleton pattern)
_scheduler_instance: Optional[StrategyScheduler] = None


def get_scheduler() -> Optional[StrategyScheduler]:
    """Get the global scheduler instance."""
    return _scheduler_instance


def create_scheduler(
    strategy_config: Optional[StrategyConfig] = None,
    risk_config: Optional[RiskConfig] = None,
    notification_config: Optional[Dict[str, Any]] = None,
) -> StrategyScheduler:
    """
    Create (or replace) the global scheduler instance.
    
    Args:
        strategy_config: Strategy configuration
        risk_config: Risk configuration
        notification_config: Notification configuration
        
    Returns:
        New StrategyScheduler instance
    """
    global _scheduler_instance
    
    # Stop existing if running
    if _scheduler_instance and _scheduler_instance.is_running:
        _scheduler_instance.stop()
    
    _scheduler_instance = StrategyScheduler(
        strategy_config=strategy_config,
        risk_config=risk_config,
        notification_config=notification_config,
    )
    
    return _scheduler_instance
