# Settlement Arbitrage Strategy - Backtest Engine
# 结算价差套利策略 - 回测引擎

"""
Backtest engine for the Settlement Arbitrage Strategy.

Supports:
- Minute-level data backtesting
- Daily-level data backtesting (fallback)
- Complete performance report generation
- Trade-by-trade recording
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from app.data_sources.cn_futures import CNFuturesDataSource
from app.strategies.settlement_arbitrage.config import StrategyConfig, RiskConfig, BacktestConfig
from app.strategies.settlement_arbitrage.vwap_calculator import VWAPCalculator
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestTrade:
    """A single trade record from backtest."""
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    base_price: float
    drop_pct: float
    vwap: Optional[float]
    level: int
    quantity: int
    multiplier: int
    gross_pnl: float
    fee: float
    net_pnl: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'entry_date': self.entry_date.isoformat(),
            'exit_date': self.exit_date.isoformat(),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'base_price': self.base_price,
            'drop_pct': self.drop_pct,
            'vwap': self.vwap,
            'level': self.level,
            'quantity': self.quantity,
            'gross_pnl': round(self.gross_pnl, 2),
            'fee': round(self.fee, 2),
            'net_pnl': round(self.net_pnl, 2),
        }


@dataclass
class BacktestReport:
    """Complete backtest results report."""
    # Parameters
    start_date: date
    end_date: date
    symbols: List[str]
    initial_capital: float
    config: Dict[str, Any]

    # Performance metrics
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    calmar_ratio: float = 0.0

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    avg_holding_days: float = 0.0

    # Equity data
    final_equity: float = 0.0
    total_pnl: float = 0.0
    total_fees: float = 0.0

    # Monthly returns
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    # Symbol analysis
    symbol_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Trade list
    trades: List[BacktestTrade] = field(default_factory=list)

    # Equity curve
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbols': self.symbols,
            'initial_capital': self.initial_capital,
            'total_return': round(self.total_return * 100, 2),
            'annual_return': round(self.annual_return * 100, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'sortino_ratio': round(self.sortino_ratio, 2),
            'max_drawdown': round(self.max_drawdown * 100, 2),
            'max_drawdown_duration': self.max_drawdown_duration,
            'calmar_ratio': round(self.calmar_ratio, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate * 100, 1),
            'profit_factor': round(self.profit_factor, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'max_win': round(self.max_win, 2),
            'max_loss': round(self.max_loss, 2),
            'avg_holding_days': round(self.avg_holding_days, 1),
            'final_equity': round(self.final_equity, 2),
            'total_pnl': round(self.total_pnl, 2),
            'total_fees': round(self.total_fees, 2),
            'monthly_returns': {k: round(v * 100, 2) for k, v in self.monthly_returns.items()},
            'symbol_stats': self.symbol_stats,
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve,
        }


class SettlementStrategyBacktest:
    """
    Backtest engine for the Settlement Arbitrage Strategy.

    Simulates the strategy over historical data:
    1. For each trading day, check if there's a significant drop after 14:30
    2. If drop > threshold_1 → simulate BUY at close price
    3. Next day → simulate SELL at open price
    4. Calculate P&L including fees

    Supports both minute-level (more accurate) and daily-level (faster) backtesting.

    Usage:
        engine = SettlementStrategyBacktest()
        report = engine.run(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            strategy_config=StrategyConfig(symbols=["IM0"]),
        )
    """

    # Default fee rates
    FEE_RATE_OPEN = 0.000023
    FEE_RATE_CLOSE = 0.000023

    def __init__(self, data_source: Optional[CNFuturesDataSource] = None):
        self.data_source = data_source or CNFuturesDataSource()

    def run(
        self,
        start_date: date,
        end_date: date,
        strategy_config: Optional[StrategyConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        backtest_config: Optional[BacktestConfig] = None,
    ) -> BacktestReport:
        """
        Run the backtest.

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            strategy_config: Strategy parameters
            risk_config: Risk parameters
            backtest_config: Backtest-specific parameters

        Returns:
            BacktestReport with full results
        """
        config = strategy_config or StrategyConfig()
        bt_config = backtest_config or BacktestConfig()
        initial_capital = bt_config.initial_capital

        logger.info(
            f"Backtest starting: {start_date} to {end_date}, "
            f"symbols={config.symbols}, capital={initial_capital}"
        )

        all_trades: List[BacktestTrade] = []
        equity_curve: List[Dict[str, Any]] = []
        equity = initial_capital

        for symbol in config.symbols:
            product = symbol[:2].upper()
            product_info = CNFuturesDataSource.PRODUCTS.get(product, {})
            multiplier = product_info.get('multiplier', 200)

            # Get daily data for the symbol
            daily_df = self._get_daily_data(symbol, start_date, end_date)
            if daily_df is None or daily_df.empty:
                logger.warning(f"No daily data for {symbol}, skipping")
                continue

            # Get minute data if available
            minute_data = None
            if bt_config.use_minute_data:
                minute_data = self._try_get_minute_data(symbol, start_date, end_date)

            # Run strategy simulation
            trades = self._simulate_strategy(
                symbol=symbol,
                daily_df=daily_df,
                minute_data=minute_data,
                config=config,
                multiplier=multiplier,
            )

            all_trades.extend(trades)

        # Sort trades by entry date
        all_trades.sort(key=lambda t: t.entry_date)

        # Build equity curve
        equity = initial_capital
        for trade in all_trades:
            equity += trade.net_pnl
            equity_curve.append({
                'date': trade.exit_date.isoformat(),
                'equity': round(equity, 2),
                'trade_pnl': round(trade.net_pnl, 2),
                'symbol': trade.symbol,
            })

        # Generate report
        report = self._generate_report(
            trades=all_trades,
            equity_curve=equity_curve,
            start_date=start_date,
            end_date=end_date,
            symbols=config.symbols,
            initial_capital=initial_capital,
            config=config,
        )

        logger.info(
            f"Backtest complete: {report.total_trades} trades, "
            f"total return={report.total_return:.2%}, "
            f"sharpe={report.sharpe_ratio:.2f}"
        )

        return report

    def _get_daily_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[pd.DataFrame]:
        """Get daily K-line data for a symbol."""
        try:
            df = self.data_source.get_kline_data(
                symbol=symbol,
                period='daily',
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            return df
        except Exception as e:
            logger.error(f"Failed to get daily data for {symbol}: {e}")
            return None

    def _try_get_minute_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[Dict[date, pd.DataFrame]]:
        """
        Try to get minute-level data.
        Returns a dict of {date: DataFrame} or None.
        """
        # Minute data retrieval is often limited, so this is best-effort
        try:
            from app.strategies.settlement_arbitrage.data_handler import MinuteDataHandler
            handler = MinuteDataHandler(data_source=self.data_source)
            result = {}

            current = start_date
            while current <= end_date:
                df = handler.load_from_local(symbol, current)
                if df is not None and not df.empty:
                    result[current] = df
                current += timedelta(days=1)

            return result if result else None
        except Exception:
            return None

    def _simulate_strategy(
        self,
        symbol: str,
        daily_df: pd.DataFrame,
        minute_data: Optional[Dict[date, pd.DataFrame]],
        config: StrategyConfig,
        multiplier: int,
    ) -> List[BacktestTrade]:
        """
        Simulate the strategy over daily data.

        For each day:
        1. If we hold a position from yesterday → close at today's open
        2. Check if today's drop meets entry threshold
        3. If yes → enter position at close

        For day-level simulation, we approximate the 14:30 drop by using
        intraday price movement (close vs previous close).
        """
        trades = []

        if daily_df is None or daily_df.empty:
            return trades

        df = daily_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)

        # State tracking
        pending_entry = None  # (entry_date, entry_price, base_price, drop_pct, vwap, level, qty)

        for i in range(1, len(df)):
            today = df.iloc[i]
            yesterday = df.iloc[i - 1]
            today_date = pd.Timestamp(today['datetime']).date()

            # Step 1: Close yesterday's position at today's open
            if pending_entry is not None:
                entry_date, entry_price, base_price, drop_pct, vwap, level, qty = pending_entry

                exit_price = float(today['open'])

                # Calculate P&L
                gross_pnl = (exit_price - entry_price) * qty * multiplier
                open_fee = entry_price * multiplier * qty * self.FEE_RATE_OPEN
                close_fee = exit_price * multiplier * qty * self.FEE_RATE_CLOSE
                fee = open_fee + close_fee
                net_pnl = gross_pnl - fee

                trade = BacktestTrade(
                    symbol=symbol,
                    entry_date=entry_date,
                    exit_date=today_date,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    base_price=base_price,
                    drop_pct=drop_pct,
                    vwap=vwap,
                    level=level,
                    quantity=qty,
                    multiplier=multiplier,
                    gross_pnl=gross_pnl,
                    fee=fee,
                    net_pnl=net_pnl,
                )
                trades.append(trade)
                pending_entry = None

            # Step 2: Check entry conditions for today
            prev_close = float(yesterday['close'])
            today_close = float(today['close'])
            today_low = float(today['low'])

            # Try minute data first
            base_price_at_1430 = None
            vwap_value = None

            if minute_data and today_date in minute_data:
                min_df = minute_data[today_date]
                base_price_at_1430 = self._get_price_at_time(min_df, time(14, 30))
                vwap_calc = VWAPCalculator()
                vwap_value = vwap_calc.calculate_vwap(min_df)

            # Fallback: approximate base price as previous close
            if base_price_at_1430 is None:
                base_price_at_1430 = prev_close

            # Calculate drop from base price
            if base_price_at_1430 > 0:
                drop_pct = (today_close - base_price_at_1430) / base_price_at_1430
            else:
                continue

            # Level 1 entry
            if drop_pct <= -config.threshold_1:
                pending_entry = (
                    today_date,
                    today_close,
                    base_price_at_1430,
                    drop_pct,
                    vwap_value,
                    2 if drop_pct <= -config.threshold_2 else 1,
                    config.position_size_1 + (
                        config.position_size_2 if drop_pct <= -config.threshold_2 else 0
                    ),
                )

        # If there's a pending entry at the end, close at last close price
        if pending_entry is not None and len(df) > 0:
            entry_date, entry_price, base_price, drop_pct, vwap, level, qty = pending_entry
            exit_price = float(df.iloc[-1]['close'])
            exit_date = pd.Timestamp(df.iloc[-1]['datetime']).date()

            gross_pnl = (exit_price - entry_price) * qty * multiplier
            open_fee = entry_price * multiplier * qty * self.FEE_RATE_OPEN
            close_fee = exit_price * multiplier * qty * self.FEE_RATE_CLOSE
            fee = open_fee + close_fee
            net_pnl = gross_pnl - fee

            trades.append(BacktestTrade(
                symbol=symbol,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                exit_price=exit_price,
                base_price=base_price,
                drop_pct=drop_pct,
                vwap=vwap,
                level=level,
                quantity=qty,
                multiplier=multiplier,
                gross_pnl=gross_pnl,
                fee=fee,
                net_pnl=net_pnl,
            ))

        return trades

    def _get_price_at_time(self, minute_df: pd.DataFrame, target: time) -> Optional[float]:
        """Get close price at a specific time from minute data."""
        if minute_df is None or minute_df.empty:
            return None

        df = minute_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])

        before = df[df['datetime'].dt.time <= target]
        if not before.empty:
            return float(before.iloc[-1]['close'])
        return None

    def _generate_report(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[Dict[str, Any]],
        start_date: date,
        end_date: date,
        symbols: List[str],
        initial_capital: float,
        config: StrategyConfig,
    ) -> BacktestReport:
        """Generate comprehensive backtest report."""

        report = BacktestReport(
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            initial_capital=initial_capital,
            config={
                'threshold_1': config.threshold_1,
                'threshold_2': config.threshold_2,
                'position_size_1': config.position_size_1,
                'position_size_2': config.position_size_2,
            },
            trades=trades,
            equity_curve=equity_curve,
        )

        if not trades:
            report.final_equity = initial_capital
            return report

        # Basic trade stats
        pnls = [t.net_pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        report.total_trades = len(trades)
        report.winning_trades = len(wins)
        report.losing_trades = len(losses)
        report.win_rate = len(wins) / len(trades) if trades else 0

        report.total_pnl = sum(pnls)
        report.total_fees = sum(t.fee for t in trades)
        report.final_equity = initial_capital + report.total_pnl

        report.avg_win = np.mean(wins) if wins else 0
        report.avg_loss = np.mean(losses) if losses else 0
        report.max_win = max(wins) if wins else 0
        report.max_loss = min(losses) if losses else 0

        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        report.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Holding period
        holding_days = [(t.exit_date - t.entry_date).days for t in trades]
        report.avg_holding_days = np.mean(holding_days) if holding_days else 0

        # Returns
        total_days = (end_date - start_date).days
        report.total_return = report.total_pnl / initial_capital
        if total_days > 0:
            years = total_days / 365.25
            report.annual_return = (1 + report.total_return) ** (1 / years) - 1 if years > 0 else 0
        else:
            report.annual_return = 0

        # Sharpe ratio (assume risk-free rate = 3%)
        if len(pnls) > 1:
            daily_returns = np.array(pnls) / initial_capital
            excess = daily_returns - 0.03 / 252
            if np.std(excess) > 0:
                report.sharpe_ratio = float(np.mean(excess) / np.std(excess) * np.sqrt(252))
            else:
                report.sharpe_ratio = 0.0

            # Sortino ratio
            downside = excess[excess < 0]
            if len(downside) > 0 and np.std(downside) > 0:
                report.sortino_ratio = np.mean(excess) / np.std(downside) * np.sqrt(252)

        # Max drawdown
        equity_values = [initial_capital]
        for pnl in pnls:
            equity_values.append(equity_values[-1] + pnl)

        peak = equity_values[0]
        max_dd = 0
        dd_start = 0
        dd_duration = 0
        max_dd_duration = 0

        for i, eq in enumerate(equity_values):
            if eq > peak:
                peak = eq
                dd_start = i
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
                max_dd_duration = i - dd_start

        report.max_drawdown = max_dd
        report.max_drawdown_duration = max_dd_duration

        # Calmar ratio
        if max_dd > 0:
            report.calmar_ratio = report.annual_return / max_dd

        # Monthly returns
        monthly = {}
        for trade in trades:
            month_key = trade.exit_date.strftime('%Y-%m')
            if month_key not in monthly:
                monthly[month_key] = 0
            monthly[month_key] += trade.net_pnl

        report.monthly_returns = {
            k: v / initial_capital for k, v in sorted(monthly.items())
        }

        # Symbol analysis
        for symbol in symbols:
            sym_trades = [t for t in trades if t.symbol == symbol]
            if not sym_trades:
                continue

            sym_pnls = [t.net_pnl for t in sym_trades]
            sym_wins = [p for p in sym_pnls if p > 0]

            report.symbol_stats[symbol] = {
                'trades': len(sym_trades),
                'total_pnl': round(sum(sym_pnls), 2),
                'win_rate': round(len(sym_wins) / len(sym_trades), 4) if sym_trades else 0,
                'avg_pnl': round(np.mean(sym_pnls), 2),
            }

        return report
