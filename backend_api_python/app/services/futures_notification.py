"""
Futures notification templates and service.

This module provides specialized notification templates and services
for Chinese index futures (IC, IM, IF, IH) settlement arbitrage strategy.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from app.services.signal_notifier import SignalNotifier
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FuturesSignalType(Enum):
    """Futures signal types"""
    BUY = "buy"
    SELL = "sell"
    PRICE_ALERT = "price_alert"
    PNL_REPORT = "pnl_report"


@dataclass
class FuturesSignalData:
    """
    Futures signal data structure.
    
    Attributes:
        signal_type: Signal type (buy, sell, price_alert, pnl_report)
        symbol: Contract code, e.g., IC0 (main contract)
        current_price: Current price
        base_price: Base price (e.g., 14:30 price)
        drop_pct: Drop percentage (negative means down)
        timestamp: Signal timestamp
        entry_price: Entry price (for sell signal)
        profit: Profit amount (for sell/report)
        profit_pct: Profit percentage
        monthly_pnl: Monthly cumulative P&L
    """
    signal_type: FuturesSignalType
    symbol: str
    current_price: float
    base_price: float
    drop_pct: float
    timestamp: datetime
    
    # Optional fields
    entry_price: Optional[float] = None
    profit: Optional[float] = None
    profit_pct: Optional[float] = None
    monthly_pnl: Optional[float] = None


# Notification templates
BUY_SIGNAL_TEMPLATE = """🚀 【买入信号】股指期货结算价套利

📊 合约: {symbol} (主力)
📉 当前价: {current_price}
📌 14:30价: {base_price}
📉 跌幅: {drop_pct:.2f}%
⏰ 时间: {time}

💡 建议: 买入1手，持有至次日开盘"""

SELL_SIGNAL_TEMPLATE = """📤 【卖出信号】股指期货结算价套利

📊 合约: {symbol} (主力)
💰 开盘价: {current_price}
📈 买入价: {entry_price}
📊 收益: {profit:.2f}元 ({profit_pct:.2f}%)
⏰ 时间: {time}

💡 建议: 开盘卖出平仓"""

PRICE_ALERT_TEMPLATE = """⚠️ 【价格预警】接近买入阈值

📊 合约: {symbol} (主力)
📉 当前跌幅: {drop_pct:.2f}%
🎯 触发阈值: 1.00%
⏰ 时间: {time}

💡 请关注: 即将触发买入信号"""

PNL_REPORT_TEMPLATE = """📊 【交易报告】股指期货结算价套利

📋 合约: {symbol} (主力)
💰 买入价: {entry_price}
💰 卖出价: {current_price}
📈 收益: {profit:.2f}元 ({profit_pct:.2f}%)
⏰ 持仓时间: 隔夜

📊 本月累计: {monthly_pnl:.2f}元"""


class FuturesNotificationTemplates:
    """
    Futures strategy notification templates.
    
    Provides methods to render notification content for different signal types.
    Each render method returns a dictionary with:
    - title: Notification title
    - plain: Plain text content
    - html: HTML formatted content (for email)
    - telegram: Telegram formatted content (HTML mode)
    """
    
    @staticmethod
    def render_buy_signal(data: FuturesSignalData) -> Dict[str, str]:
        """
        Render buy signal notification.
        
        Args:
            data: FuturesSignalData with signal details
            
        Returns:
            Dictionary with title, plain, html, telegram keys
        """
        time_str = data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format drop percentage (show as positive for display)
        drop_display = abs(data.drop_pct) * 100  # Convert to percentage
        
        title = f"【买入信号】{data.symbol} 跌幅达 {drop_display:.2f}%"
        
        plain = BUY_SIGNAL_TEMPLATE.format(
            symbol=data.symbol,
            current_price=f"{data.current_price:.2f}",
            base_price=f"{data.base_price:.2f}",
            drop_pct=drop_display,
            time=time_str
        )
        
        # Telegram HTML format
        telegram = f"""<b>🚀 【买入信号】股指期货结算价套利</b>

<b>📊 合约:</b> <code>{html.escape(data.symbol)}</code> (主力)
<b>📉 当前价:</b> <code>{data.current_price:.2f}</code>
<b>📌 14:30价:</b> <code>{data.base_price:.2f}</code>
<b>📉 跌幅:</b> <code>{drop_display:.2f}%</code>
<b>⏰ 时间:</b> <code>{html.escape(time_str)}</code>

💡 <i>建议: 买入1手，持有至次日开盘</i>"""

        # Email HTML format
        email_html = FuturesNotificationTemplates._build_email_html(
            title="🚀 【买入信号】股指期货结算价套利",
            rows=[
                ("合约", f"{data.symbol} (主力)"),
                ("当前价", f"{data.current_price:.2f}"),
                ("14:30价", f"{data.base_price:.2f}"),
                ("跌幅", f"{drop_display:.2f}%"),
                ("时间", time_str),
                ("建议", "买入1手，持有至次日开盘"),
            ],
            color="#2ECC71"
        )
        
        return {
            "title": title,
            "plain": plain,
            "html": email_html,
            "telegram": telegram
        }
    
    @staticmethod
    def render_sell_signal(data: FuturesSignalData) -> Dict[str, str]:
        """
        Render sell signal notification.
        
        Args:
            data: FuturesSignalData with signal details including entry_price
            
        Returns:
            Dictionary with title, plain, html, telegram keys
        """
        time_str = data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        entry_price = data.entry_price or 0.0
        profit = data.profit or 0.0
        profit_pct = (data.profit_pct or 0.0) * 100  # Convert to percentage
        
        title = f"【卖出信号】{data.symbol} 收益 {profit:.2f}元"
        
        plain = SELL_SIGNAL_TEMPLATE.format(
            symbol=data.symbol,
            current_price=f"{data.current_price:.2f}",
            entry_price=f"{entry_price:.2f}",
            profit=profit,
            profit_pct=profit_pct,
            time=time_str
        )
        
        # Telegram HTML format
        profit_sign = "+" if profit >= 0 else ""
        telegram = f"""<b>📤 【卖出信号】股指期货结算价套利</b>

<b>📊 合约:</b> <code>{html.escape(data.symbol)}</code> (主力)
<b>💰 开盘价:</b> <code>{data.current_price:.2f}</code>
<b>📈 买入价:</b> <code>{entry_price:.2f}</code>
<b>📊 收益:</b> <code>{profit_sign}{profit:.2f}元 ({profit_sign}{profit_pct:.2f}%)</code>
<b>⏰ 时间:</b> <code>{html.escape(time_str)}</code>

💡 <i>建议: 开盘卖出平仓</i>"""

        # Email HTML format
        email_html = FuturesNotificationTemplates._build_email_html(
            title="📤 【卖出信号】股指期货结算价套利",
            rows=[
                ("合约", f"{data.symbol} (主力)"),
                ("开盘价", f"{data.current_price:.2f}"),
                ("买入价", f"{entry_price:.2f}"),
                ("收益", f"{profit_sign}{profit:.2f}元 ({profit_sign}{profit_pct:.2f}%)"),
                ("时间", time_str),
                ("建议", "开盘卖出平仓"),
            ],
            color="#E74C3C"
        )
        
        return {
            "title": title,
            "plain": plain,
            "html": email_html,
            "telegram": telegram
        }
    
    @staticmethod
    def render_price_alert(data: FuturesSignalData) -> Dict[str, str]:
        """
        Render price alert notification.
        
        Args:
            data: FuturesSignalData with current drop percentage
            
        Returns:
            Dictionary with title, plain, html, telegram keys
        """
        time_str = data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        drop_display = abs(data.drop_pct) * 100  # Convert to percentage
        
        title = f"【价格预警】{data.symbol} 跌幅 {drop_display:.2f}%"
        
        plain = PRICE_ALERT_TEMPLATE.format(
            symbol=data.symbol,
            drop_pct=drop_display,
            time=time_str
        )
        
        # Telegram HTML format
        telegram = f"""<b>⚠️ 【价格预警】接近买入阈值</b>

<b>📊 合约:</b> <code>{html.escape(data.symbol)}</code> (主力)
<b>📉 当前跌幅:</b> <code>{drop_display:.2f}%</code>
<b>🎯 触发阈值:</b> <code>1.00%</code>
<b>⏰ 时间:</b> <code>{html.escape(time_str)}</code>

💡 <i>请关注: 即将触发买入信号</i>"""

        # Email HTML format
        email_html = FuturesNotificationTemplates._build_email_html(
            title="⚠️ 【价格预警】接近买入阈值",
            rows=[
                ("合约", f"{data.symbol} (主力)"),
                ("当前跌幅", f"{drop_display:.2f}%"),
                ("触发阈值", "1.00%"),
                ("时间", time_str),
                ("提示", "即将触发买入信号"),
            ],
            color="#F39C12"
        )
        
        return {
            "title": title,
            "plain": plain,
            "html": email_html,
            "telegram": telegram
        }
    
    @staticmethod
    def render_pnl_report(data: FuturesSignalData) -> Dict[str, str]:
        """
        Render P&L report notification.
        
        Args:
            data: FuturesSignalData with full trading details
            
        Returns:
            Dictionary with title, plain, html, telegram keys
        """
        time_str = data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        entry_price = data.entry_price or 0.0
        profit = data.profit or 0.0
        profit_pct = (data.profit_pct or 0.0) * 100  # Convert to percentage
        monthly_pnl = data.monthly_pnl or 0.0
        
        title = f"【交易报告】{data.symbol} 本次收益 {profit:.2f}元"
        
        plain = PNL_REPORT_TEMPLATE.format(
            symbol=data.symbol,
            entry_price=f"{entry_price:.2f}",
            current_price=f"{data.current_price:.2f}",
            profit=profit,
            profit_pct=profit_pct,
            monthly_pnl=monthly_pnl
        )
        
        # Telegram HTML format
        profit_sign = "+" if profit >= 0 else ""
        monthly_sign = "+" if monthly_pnl >= 0 else ""
        telegram = f"""<b>📊 【交易报告】股指期货结算价套利</b>

<b>📋 合约:</b> <code>{html.escape(data.symbol)}</code> (主力)
<b>💰 买入价:</b> <code>{entry_price:.2f}</code>
<b>💰 卖出价:</b> <code>{data.current_price:.2f}</code>
<b>📈 收益:</b> <code>{profit_sign}{profit:.2f}元 ({profit_sign}{profit_pct:.2f}%)</code>
<b>⏰ 持仓时间:</b> <code>隔夜</code>

<b>📊 本月累计:</b> <code>{monthly_sign}{monthly_pnl:.2f}元</code>"""

        # Email HTML format
        email_html = FuturesNotificationTemplates._build_email_html(
            title="📊 【交易报告】股指期货结算价套利",
            rows=[
                ("合约", f"{data.symbol} (主力)"),
                ("买入价", f"{entry_price:.2f}"),
                ("卖出价", f"{data.current_price:.2f}"),
                ("收益", f"{profit_sign}{profit:.2f}元 ({profit_sign}{profit_pct:.2f}%)"),
                ("持仓时间", "隔夜"),
                ("本月累计", f"{monthly_sign}{monthly_pnl:.2f}元"),
            ],
            color="#3498DB"
        )
        
        return {
            "title": title,
            "plain": plain,
            "html": email_html,
            "telegram": telegram
        }
    
    @staticmethod
    def _build_email_html(title: str, rows: list, color: str = "#3498DB") -> str:
        """Build HTML email content with a styled table."""
        def esc(s: Any) -> str:
            return html.escape(str(s or ""))
        
        tr_html = "\n".join([
            f"""<tr>
                <td style='padding:10px 12px;border-top:1px solid #eaecef;color:#57606a;width:120px;'>{esc(k)}</td>
                <td style='padding:10px 12px;border-top:1px solid #eaecef;color:#24292f;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;'>{esc(v)}</td>
            </tr>"""
            for k, v in rows
        ])
        
        return f"""\
<!doctype html>
<html>
<body style="margin:0;padding:0;background:#f6f8fa;">
<div style="max-width:640px;margin:0 auto;padding:24px;">
    <div style="background:{color};color:#ffffff;padding:16px 18px;border-radius:12px 12px 0 0;">
        <div style="font-size:16px;letter-spacing:0.2px;font-weight:600;">{esc(title)}</div>
    </div>
    <div style="background:#ffffff;border:1px solid #eaecef;border-top:0;border-radius:0 0 12px 12px;overflow:hidden;">
        <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;">
            {tr_html}
        </table>
        <div style="padding:14px 16px;color:#6e7781;font-size:12px;border-top:1px solid #eaecef;">
            Generated by QuantDinger Futures Strategy
        </div>
    </div>
</div>
</body>
</html>
"""


class FuturesNotificationService:
    """
    Futures strategy notification service.
    
    Wraps SignalNotifier to provide specialized interfaces for futures strategy signals.
    Handles rendering of templates and dispatching notifications to configured channels.
    """
    
    def __init__(self):
        self.notifier = SignalNotifier()
        self.templates = FuturesNotificationTemplates()
    
    def send_buy_signal(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send buy signal notification.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            data: Signal data
            notification_config: Notification configuration (channels, targets)
            
        Returns:
            Dictionary with results for each channel
            e.g., {"telegram": {"ok": True}, "email": {"ok": True}, ...}
        """
        rendered = self.templates.render_buy_signal(data)
        return self._send_notification(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            data=data,
            rendered=rendered,
            signal_type="open_long",
            notification_config=notification_config
        )
    
    def send_sell_signal(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send sell signal notification.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name  
            data: Signal data with entry_price and profit
            notification_config: Notification configuration
            
        Returns:
            Dictionary with results for each channel
        """
        rendered = self.templates.render_sell_signal(data)
        return self._send_notification(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            data=data,
            rendered=rendered,
            signal_type="close_long",
            notification_config=notification_config
        )
    
    def send_price_alert(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send price alert notification.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            data: Signal data with current drop percentage
            notification_config: Notification configuration
            
        Returns:
            Dictionary with results for each channel
        """
        rendered = self.templates.render_price_alert(data)
        return self._send_notification(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            data=data,
            rendered=rendered,
            signal_type="price_alert",
            notification_config=notification_config
        )
    
    def send_pnl_report(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send P&L report notification.
        
        Args:
            strategy_id: Strategy ID
            strategy_name: Strategy name
            data: Signal data with full trading details
            notification_config: Notification configuration
            
        Returns:
            Dictionary with results for each channel
        """
        rendered = self.templates.render_pnl_report(data)
        return self._send_notification(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            data=data,
            rendered=rendered,
            signal_type="pnl_report",
            notification_config=notification_config
        )
    
    def _send_notification(
        self,
        strategy_id: int,
        strategy_name: str,
        data: FuturesSignalData,
        rendered: Dict[str, str],
        signal_type: str,
        notification_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to send notification using SignalNotifier.
        
        This method adapts the rendered templates to the SignalNotifier interface.
        """
        try:
            # Build extra data with rendered content
            extra = {
                "futures_signal": {
                    "type": data.signal_type.value,
                    "symbol": data.symbol,
                    "current_price": data.current_price,
                    "base_price": data.base_price,
                    "drop_pct": data.drop_pct,
                    "entry_price": data.entry_price,
                    "profit": data.profit,
                    "profit_pct": data.profit_pct,
                    "monthly_pnl": data.monthly_pnl,
                },
                "rendered_title": rendered.get("title", ""),
                "rendered_plain": rendered.get("plain", ""),
                "rendered_telegram": rendered.get("telegram", ""),
                "rendered_html": rendered.get("html", ""),
            }
            
            # Use SignalNotifier to dispatch
            result = self.notifier.notify_signal(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                symbol=data.symbol,
                signal_type=signal_type,
                price=data.current_price,
                direction="long",
                notification_config=notification_config,
                extra=extra,
            )
            
            logger.info(
                f"Futures notification sent: strategy_id={strategy_id} "
                f"signal_type={data.signal_type.value} symbol={data.symbol}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send futures notification: {e}")
            return {"error": {"ok": False, "error": str(e)}}


# Test function
def test_futures_notification():
    """Test the futures notification module."""
    from datetime import datetime
    
    service = FuturesNotificationService()
    
    # Test 1: Render buy signal
    buy_data = FuturesSignalData(
        signal_type=FuturesSignalType.BUY,
        symbol="IC0",
        current_price=5450,
        base_price=5500,
        drop_pct=-0.0091,  # -0.91%
        timestamp=datetime.now()
    )
    rendered = service.templates.render_buy_signal(buy_data)
    assert "title" in rendered
    assert "5450" in rendered["plain"]
    print("✅ Test 1 passed: Buy signal rendered")
    
    # Test 2: Render sell signal
    sell_data = FuturesSignalData(
        signal_type=FuturesSignalType.SELL,
        symbol="IC0",
        current_price=5520,
        base_price=5500,
        drop_pct=0.0036,  # +0.36%
        timestamp=datetime.now(),
        entry_price=5450,
        profit=14000,
        profit_pct=0.0128  # 1.28%
    )
    rendered = service.templates.render_sell_signal(sell_data)
    assert "14000" in rendered["plain"]
    print("✅ Test 2 passed: Sell signal rendered")
    
    # Test 3: Render price alert
    alert_data = FuturesSignalData(
        signal_type=FuturesSignalType.PRICE_ALERT,
        symbol="IC0",
        current_price=5455,
        base_price=5500,
        drop_pct=-0.0082,  # -0.82%
        timestamp=datetime.now()
    )
    rendered = service.templates.render_price_alert(alert_data)
    assert "预警" in rendered["title"]
    print("✅ Test 3 passed: Price alert rendered")
    
    # Test 4: Render PnL report
    report_data = FuturesSignalData(
        signal_type=FuturesSignalType.PNL_REPORT,
        symbol="IC0",
        current_price=5520,
        base_price=5500,
        drop_pct=0.0036,
        timestamp=datetime.now(),
        entry_price=5450,
        profit=14000,
        profit_pct=0.0128,
        monthly_pnl=42000
    )
    rendered = service.templates.render_pnl_report(report_data)
    assert "42000" in rendered["plain"]
    print("✅ Test 4 passed: PnL report rendered")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_futures_notification()
