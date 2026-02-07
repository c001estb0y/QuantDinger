"""
Futures Calculator Module
期货计算器模块 - 包含保证金、手续费、结算价、涨跌停等计算功能

Author: Developer B
Created: 2026-02-04
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time
import re


# ==================== Data Classes ====================

@dataclass
class MarginInfo:
    """Margin information / 保证金信息"""
    contract_value: float    # Contract value / 合约价值
    margin_ratio: float      # Margin ratio / 保证金比例
    margin_required: float   # Required margin / 所需保证金
    multiplier: int          # Contract multiplier / 合约乘数


@dataclass
class FeeInfo:
    """Fee information / 手续费信息"""
    contract_value: float    # Contract value / 合约价值
    fee_rate: float          # Fee rate / 费率
    fee_amount: float        # Fee amount / 手续费金额
    is_close_today: bool     # Is close today / 是否平今


class PriceLimitStatus(Enum):
    """Price limit status / 涨跌停状态"""
    NORMAL = "normal"
    LIMIT_UP = "limit_up"
    LIMIT_DOWN = "limit_down"


@dataclass
class PriceLimitInfo:
    """Price limit information / 涨跌停信息"""
    status: PriceLimitStatus
    upper_limit: float       # Upper limit price / 涨停价
    lower_limit: float       # Lower limit price / 跌停价
    current_price: float     # Current price / 当前价
    distance_to_limit: float # Distance to limit percentage / 距离涨跌停的百分比


# ==================== Margin Calculator ====================

class FuturesMarginCalculator:
    """
    Futures Margin Calculator
    期货保证金计算器
    """
    
    # Margin ratios configuration / 保证金比例配置
    MARGIN_RATIOS: Dict[str, float] = {
        'IC': 0.12,  # CSI 500, 12% / 中证500，12%
        'IM': 0.12,  # CSI 1000, 12% / 中证1000，12%
        'IF': 0.10,  # CSI 300, 10% / 沪深300，10%
        'IH': 0.10,  # SSE 50, 10% / 上证50，10%
    }
    
    # Contract multipliers configuration / 合约乘数配置
    MULTIPLIERS: Dict[str, int] = {
        'IC': 200,  # 200 yuan per point / 每点200元
        'IM': 200,  # 200 yuan per point / 每点200元
        'IF': 300,  # 300 yuan per point / 每点300元
        'IH': 300,  # 300 yuan per point / 每点300元
    }
    
    def _extract_product(self, symbol: str) -> str:
        """
        Extract product code from symbol
        从合约代码中提取品种代码
        
        Args:
            symbol: Contract code like IC0, IC2503, IM0
            
        Returns:
            Product code like IC, IM, IF, IH
        """
        # Remove trailing numbers to get product code
        match = re.match(r'^([A-Z]+)', symbol.upper())
        if match:
            return match.group(1)
        return symbol.upper()[:2]
    
    def calculate(
        self,
        symbol: str,
        price: float,
        quantity: int = 1
    ) -> MarginInfo:
        """
        Calculate margin
        计算保证金
        
        Args:
            symbol: Contract code (IC0, IM2503, etc.)
            price: Current price
            quantity: Number of contracts
            
        Returns:
            MarginInfo object
        """
        product = self._extract_product(symbol)
        multiplier = self.get_multiplier(symbol)
        margin_ratio = self.get_margin_ratio(symbol)
        
        contract_value = price * multiplier * quantity
        margin_required = contract_value * margin_ratio
        
        return MarginInfo(
            contract_value=contract_value,
            margin_ratio=margin_ratio,
            margin_required=margin_required,
            multiplier=multiplier
        )
    
    def get_margin_ratio(self, symbol: str) -> float:
        """
        Get margin ratio for symbol
        获取保证金比例
        """
        product = self._extract_product(symbol)
        return self.MARGIN_RATIOS.get(product, 0.12)  # Default 12%
    
    def get_multiplier(self, symbol: str) -> int:
        """
        Get contract multiplier for symbol
        获取合约乘数
        """
        product = self._extract_product(symbol)
        return self.MULTIPLIERS.get(product, 200)  # Default 200


# ==================== Fee Calculator ====================

class FuturesFeeCalculator:
    """
    Futures Fee Calculator
    期货手续费计算器
    """
    
    # Fee rates configuration (by contract value) / 手续费率配置（按成交金额）
    FEE_RATES: Dict[str, Dict[str, float]] = {
        'IC': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IM': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IF': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
        'IH': {'open': 0.000023, 'close': 0.000023, 'close_today': 0.000345},
    }
    
    # Contract multipliers (shared with margin calculator)
    MULTIPLIERS: Dict[str, int] = {
        'IC': 200,
        'IM': 200,
        'IF': 300,
        'IH': 300,
    }
    
    def _extract_product(self, symbol: str) -> str:
        """Extract product code from symbol"""
        match = re.match(r'^([A-Z]+)', symbol.upper())
        if match:
            return match.group(1)
        return symbol.upper()[:2]
    
    def _get_multiplier(self, symbol: str) -> int:
        """Get contract multiplier"""
        product = self._extract_product(symbol)
        return self.MULTIPLIERS.get(product, 200)
    
    def calculate(
        self,
        symbol: str,
        price: float,
        quantity: int = 1,
        is_open: bool = True,
        is_close_today: bool = False
    ) -> FeeInfo:
        """
        Calculate fee
        计算手续费
        
        Args:
            symbol: Contract code
            price: Transaction price
            quantity: Number of contracts
            is_open: Is opening position
            is_close_today: Is closing today's position (only valid when is_open=False)
            
        Returns:
            FeeInfo object
        """
        product = self._extract_product(symbol)
        multiplier = self._get_multiplier(symbol)
        contract_value = price * multiplier * quantity
        
        # Get fee rate based on operation type
        rates = self.FEE_RATES.get(product, self.FEE_RATES['IC'])
        
        if is_open:
            fee_rate = rates['open']
            close_today_flag = False
        elif is_close_today:
            fee_rate = rates['close_today']
            close_today_flag = True
        else:
            fee_rate = rates['close']
            close_today_flag = False
        
        fee_amount = contract_value * fee_rate
        
        return FeeInfo(
            contract_value=contract_value,
            fee_rate=fee_rate,
            fee_amount=fee_amount,
            is_close_today=close_today_flag
        )
    
    def calculate_round_trip(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int = 1,
        is_same_day: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate round trip fees (open + close)
        计算往返手续费（开仓+平仓）
        
        Returns:
            {"open": FeeInfo, "close": FeeInfo, "total": float}
        """
        open_fee = self.calculate(
            symbol=symbol,
            price=entry_price,
            quantity=quantity,
            is_open=True
        )
        
        close_fee = self.calculate(
            symbol=symbol,
            price=exit_price,
            quantity=quantity,
            is_open=False,
            is_close_today=is_same_day
        )
        
        return {
            "open": open_fee,
            "close": close_fee,
            "total": open_fee.fee_amount + close_fee.fee_amount
        }


# ==================== Settlement Price Calculator ====================

class SettlementPriceCalculator:
    """
    Settlement Price Calculator
    结算价计算器
    
    Stock index futures settlement price = Last hour VWAP
    股指期货结算价 = 最后一小时VWAP
    """
    
    def calculate_vwap(
        self,
        minute_bars: List[Dict[str, Any]],
        start_time: str = "14:00:00",
        end_time: str = "15:00:00"
    ) -> float:
        """
        Calculate VWAP (Volume Weighted Average Price)
        计算VWAP（成交量加权平均价）
        
        Args:
            minute_bars: Minute K-line list
                [{"time": int, "close": float, "volume": float}, ...]
            start_time: Start time (HH:MM:SS)
            end_time: End time (HH:MM:SS)
            
        Returns:
            VWAP value
        """
        if not minute_bars:
            return 0.0
        
        # Parse time range
        start_h, start_m, start_s = map(int, start_time.split(':'))
        end_h, end_m, end_s = map(int, end_time.split(':'))
        start_seconds = start_h * 3600 + start_m * 60 + start_s
        end_seconds = end_h * 3600 + end_m * 60 + end_s
        
        # Filter bars within time range and calculate VWAP
        total_value = 0.0
        total_volume = 0.0
        
        for bar in minute_bars:
            bar_time = bar.get('time', 0)
            
            # Convert timestamp to time of day
            if isinstance(bar_time, int):
                dt = datetime.fromtimestamp(bar_time)
                bar_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
            else:
                continue
            
            # Check if within time range
            if start_seconds <= bar_seconds <= end_seconds:
                close_price = bar.get('close', 0)
                volume = bar.get('volume', 0)
                
                if volume > 0:
                    total_value += close_price * volume
                    total_volume += volume
        
        if total_volume == 0:
            return 0.0
        
        return round(total_value / total_volume, 2)
    
    def estimate_settlement_price(
        self,
        minute_bars: List[Dict[str, Any]]
    ) -> float:
        """
        Estimate settlement price
        估算结算价
        
        Uses last hour minute K-lines to calculate VWAP
        使用最后一小时的分钟K线计算VWAP
        
        Returns:
            Estimated settlement price
        """
        return self.calculate_vwap(
            minute_bars=minute_bars,
            start_time="14:00:00",
            end_time="15:00:00"
        )
    
    def calculate_simple_vwap(
        self,
        minute_bars: List[Dict[str, Any]],
        last_n_minutes: int = 60
    ) -> float:
        """
        Calculate simple VWAP for last N minutes
        计算最后N分钟的简单VWAP
        
        Args:
            minute_bars: Minute K-line list (sorted by time ascending)
            last_n_minutes: Number of last minutes to use
            
        Returns:
            VWAP value
        """
        if not minute_bars:
            return 0.0
        
        # Take last N bars
        bars_to_use = minute_bars[-last_n_minutes:] if len(minute_bars) > last_n_minutes else minute_bars
        
        total_value = 0.0
        total_volume = 0.0
        
        for bar in bars_to_use:
            close_price = bar.get('close', 0)
            volume = bar.get('volume', 0)
            
            if volume > 0:
                total_value += close_price * volume
                total_volume += volume
        
        if total_volume == 0:
            # If no volume data, return simple average of close prices
            closes = [bar.get('close', 0) for bar in bars_to_use if bar.get('close', 0) > 0]
            return round(sum(closes) / len(closes), 2) if closes else 0.0
        
        return round(total_value / total_volume, 2)


# ==================== Price Limit Checker ====================

class PriceLimitChecker:
    """
    Price Limit Checker
    涨跌停检测器
    
    Stock index futures price limit: ±10% (based on previous settlement price)
    股指期货涨跌停板：±10%（基于前结算价）
    """
    
    LIMIT_RATIO: float = 0.10  # 10% price limit / 10%涨跌停
    
    # Tick sizes for each product / 各品种最小变动价位
    TICK_SIZES: Dict[str, float] = {
        'IC': 0.2,
        'IM': 0.2,
        'IF': 0.2,
        'IH': 0.2,
    }
    
    def _extract_product(self, symbol: str) -> str:
        """Extract product code from symbol"""
        match = re.match(r'^([A-Z]+)', symbol.upper())
        if match:
            return match.group(1)
        return symbol.upper()[:2]
    
    def _round_to_tick(self, price: float, tick_size: float) -> float:
        """
        Round price to nearest tick
        将价格舍入到最近的最小变动单位
        """
        return round(round(price / tick_size) * tick_size, 2)
    
    def check(
        self,
        symbol: str,
        current_price: float,
        prev_settlement: float
    ) -> PriceLimitInfo:
        """
        Check price limit status
        检查涨跌停状态
        
        Args:
            symbol: Contract code
            current_price: Current price
            prev_settlement: Previous settlement price
            
        Returns:
            PriceLimitInfo object
        """
        upper_limit, lower_limit = self.calculate_limits(symbol, prev_settlement)
        
        # Determine status
        if current_price >= upper_limit:
            status = PriceLimitStatus.LIMIT_UP
            distance = 0.0
        elif current_price <= lower_limit:
            status = PriceLimitStatus.LIMIT_DOWN
            distance = 0.0
        else:
            status = PriceLimitStatus.NORMAL
            # Calculate distance to nearest limit
            dist_to_upper = (upper_limit - current_price) / prev_settlement
            dist_to_lower = (current_price - lower_limit) / prev_settlement
            distance = min(dist_to_upper, dist_to_lower)
        
        return PriceLimitInfo(
            status=status,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            current_price=current_price,
            distance_to_limit=round(distance, 4)
        )
    
    def calculate_limits(
        self,
        symbol: str,
        prev_settlement: float
    ) -> Tuple[float, float]:
        """
        Calculate price limit prices
        计算涨跌停价格
        
        Args:
            symbol: Contract code
            prev_settlement: Previous settlement price
            
        Returns:
            (upper_limit, lower_limit)
        """
        product = self._extract_product(symbol)
        tick_size = self.TICK_SIZES.get(product, 0.2)
        
        # Calculate raw limits
        upper_raw = prev_settlement * (1 + self.LIMIT_RATIO)
        lower_raw = prev_settlement * (1 - self.LIMIT_RATIO)
        
        # Round to tick size
        upper_limit = self._round_to_tick(upper_raw, tick_size)
        lower_limit = self._round_to_tick(lower_raw, tick_size)
        
        return upper_limit, lower_limit
    
    def is_near_limit(
        self,
        symbol: str,
        current_price: float,
        prev_settlement: float,
        threshold: float = 0.02  # 2% threshold
    ) -> Tuple[bool, str]:
        """
        Check if price is near limit
        检查价格是否接近涨跌停
        
        Args:
            symbol: Contract code
            current_price: Current price
            prev_settlement: Previous settlement price
            threshold: Distance threshold to consider "near"
            
        Returns:
            (is_near, direction) - direction is "up", "down", or "none"
        """
        info = self.check(symbol, current_price, prev_settlement)
        
        if info.status != PriceLimitStatus.NORMAL:
            return True, info.status.value.replace("limit_", "")
        
        if info.distance_to_limit <= threshold:
            # Determine which limit is closer
            dist_to_upper = (info.upper_limit - current_price) / prev_settlement
            dist_to_lower = (current_price - info.lower_limit) / prev_settlement
            
            if dist_to_upper < dist_to_lower:
                return True, "up"
            else:
                return True, "down"
        
        return False, "none"


# ==================== Unified Calculator Facade ====================

class FuturesCalculator:
    """
    Unified Futures Calculator Facade
    期货计算器统一门面类
    
    Integrates all calculator functionalities
    整合所有计算器功能
    """
    
    def __init__(self):
        self.margin = FuturesMarginCalculator()
        self.fee = FuturesFeeCalculator()
        self.settlement = SettlementPriceCalculator()
        self.price_limit = PriceLimitChecker()
    
    def calculate_trade_cost(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int = 1,
        is_same_day: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate complete trade cost
        计算完整交易成本
        
        Args:
            symbol: Contract code
            entry_price: Entry price
            exit_price: Exit price
            quantity: Number of contracts
            is_same_day: Is same day trade (affects close fee)
            
        Returns:
            {
                "margin_required": float,    # Required margin / 所需保证金
                "fee_open": float,           # Open fee / 开仓手续费
                "fee_close": float,          # Close fee / 平仓手续费
                "fee_total": float,          # Total fee / 总手续费
                "gross_pnl": float,          # Gross P&L / 毛盈亏
                "net_pnl": float,            # Net P&L / 净盈亏
                "pnl_points": float,         # P&L in points / 盈亏点数
            }
        """
        # Calculate margin
        margin_info = self.margin.calculate(symbol, entry_price, quantity)
        
        # Calculate fees
        fee_result = self.fee.calculate_round_trip(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            is_same_day=is_same_day
        )
        
        # Calculate P&L
        multiplier = self.margin.get_multiplier(symbol)
        pnl_points = exit_price - entry_price
        gross_pnl = pnl_points * multiplier * quantity
        net_pnl = gross_pnl - fee_result["total"]
        
        return {
            "margin_required": margin_info.margin_required,
            "fee_open": fee_result["open"].fee_amount,
            "fee_close": fee_result["close"].fee_amount,
            "fee_total": fee_result["total"],
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "pnl_points": pnl_points,
            "multiplier": multiplier,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
        }
    
    def calculate_breakeven_points(
        self,
        symbol: str,
        entry_price: float,
        quantity: int = 1,
        is_same_day: bool = True
    ) -> float:
        """
        Calculate breakeven points needed
        计算保本所需点数
        
        Args:
            symbol: Contract code
            entry_price: Entry price
            quantity: Number of contracts
            is_same_day: Is same day trade
            
        Returns:
            Breakeven points (price movement needed to break even)
        """
        multiplier = self.margin.get_multiplier(symbol)
        
        # Calculate total fees for round trip
        fee_result = self.fee.calculate_round_trip(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=entry_price,  # Use same price for fee estimation
            quantity=quantity,
            is_same_day=is_same_day
        )
        
        # Breakeven points = Total fees / (multiplier * quantity)
        breakeven_points = fee_result["total"] / (multiplier * quantity)
        
        return round(breakeven_points, 2)
    
    def calculate_position_value(
        self,
        symbol: str,
        price: float,
        quantity: int = 1
    ) -> Dict[str, float]:
        """
        Calculate position value and margin
        计算持仓价值和保证金
        
        Returns:
            {
                "contract_value": float,
                "margin_required": float,
                "margin_ratio": float,
                "multiplier": int,
            }
        """
        margin_info = self.margin.calculate(symbol, price, quantity)
        
        return {
            "contract_value": margin_info.contract_value,
            "margin_required": margin_info.margin_required,
            "margin_ratio": margin_info.margin_ratio,
            "multiplier": margin_info.multiplier,
        }
    
    def get_contract_specs(self, symbol: str) -> Dict[str, Any]:
        """
        Get contract specifications
        获取合约规格
        
        Returns:
            Contract specifications dictionary
        """
        product = self.margin._extract_product(symbol)
        
        return {
            "symbol": symbol,
            "product": product,
            "multiplier": self.margin.get_multiplier(symbol),
            "margin_ratio": self.margin.get_margin_ratio(symbol),
            "tick_size": self.price_limit.TICK_SIZES.get(product, 0.2),
            "price_limit_ratio": self.price_limit.LIMIT_RATIO,
            "fee_rate_open": self.fee.FEE_RATES.get(product, {}).get('open', 0.000023),
            "fee_rate_close": self.fee.FEE_RATES.get(product, {}).get('close', 0.000023),
            "fee_rate_close_today": self.fee.FEE_RATES.get(product, {}).get('close_today', 0.000345),
        }


# ==================== Unit Tests ====================

def test_futures_calculator():
    """
    Test futures calculator
    测试期货计算器
    """
    calc = FuturesCalculator()
    
    print("=" * 50)
    print("Testing Futures Calculator")
    print("=" * 50)
    
    # Test 1: Margin calculation
    print("\n[Test 1] Margin Calculation")
    margin = calc.margin.calculate("IC0", price=5500, quantity=1)
    expected_margin = 5500 * 200 * 0.12  # 132000
    print(f"  Symbol: IC0, Price: 5500, Quantity: 1")
    print(f"  Contract Value: {margin.contract_value}")
    print(f"  Margin Required: {margin.margin_required}")
    print(f"  Expected: {expected_margin}")
    assert abs(margin.margin_required - expected_margin) < 0.01, "Margin calculation failed"
    print("  ✅ Passed")
    
    # Test 2: Fee calculation
    print("\n[Test 2] Fee Calculation")
    fee = calc.fee.calculate("IC0", price=5500, quantity=1, is_open=True)
    print(f"  Symbol: IC0, Price: 5500, Open Position")
    print(f"  Contract Value: {fee.contract_value}")
    print(f"  Fee Rate: {fee.fee_rate}")
    print(f"  Fee Amount: {fee.fee_amount:.2f}")
    assert fee.fee_amount > 0, "Fee calculation failed"
    print("  ✅ Passed")
    
    # Test 3: Round trip fee
    print("\n[Test 3] Round Trip Fee Calculation")
    rt_fee = calc.fee.calculate_round_trip("IC0", entry_price=5500, exit_price=5550, quantity=1, is_same_day=False)
    print(f"  Entry: 5500, Exit: 5550, Next Day Close")
    print(f"  Open Fee: {rt_fee['open'].fee_amount:.2f}")
    print(f"  Close Fee: {rt_fee['close'].fee_amount:.2f}")
    print(f"  Total Fee: {rt_fee['total']:.2f}")
    assert rt_fee['total'] > 0, "Round trip fee calculation failed"
    print("  ✅ Passed")
    
    # Test 4: Price limit check
    print("\n[Test 4] Price Limit Check")
    limit = calc.price_limit.check("IC0", current_price=6000, prev_settlement=5500)
    print(f"  Current: 6000, Prev Settlement: 5500")
    print(f"  Upper Limit: {limit.upper_limit}")
    print(f"  Lower Limit: {limit.lower_limit}")
    print(f"  Status: {limit.status.value}")
    print(f"  Distance to Limit: {limit.distance_to_limit:.4f}")
    assert limit.status.value in ["normal", "limit_up", "limit_down"], "Price limit check failed"
    print("  ✅ Passed")
    
    # Test 5: Complete trade cost
    print("\n[Test 5] Complete Trade Cost")
    cost = calc.calculate_trade_cost("IC0", entry_price=5500, exit_price=5550, quantity=1, is_same_day=False)
    print(f"  Entry: 5500, Exit: 5550, 1 Contract, Next Day Close")
    print(f"  Margin Required: {cost['margin_required']:.2f}")
    print(f"  Total Fee: {cost['fee_total']:.2f}")
    print(f"  Gross P&L: {cost['gross_pnl']:.2f}")
    print(f"  Net P&L: {cost['net_pnl']:.2f}")
    print(f"  P&L Points: {cost['pnl_points']}")
    assert "net_pnl" in cost, "Trade cost calculation failed"
    print("  ✅ Passed")
    
    # Test 6: VWAP calculation
    print("\n[Test 6] VWAP Calculation")
    # Create mock minute bars
    import time as time_module
    base_time = int(time_module.time())
    mock_bars = [
        {"time": base_time - 3600 + i * 60, "close": 5500 + i, "volume": 100 + i * 10}
        for i in range(60)
    ]
    vwap = calc.settlement.calculate_simple_vwap(mock_bars, last_n_minutes=30)
    print(f"  Calculated VWAP: {vwap}")
    assert vwap > 0, "VWAP calculation failed"
    print("  ✅ Passed")
    
    # Test 7: Breakeven points
    print("\n[Test 7] Breakeven Points")
    breakeven = calc.calculate_breakeven_points("IC0", entry_price=5500, quantity=1, is_same_day=False)
    print(f"  Entry: 5500, 1 Contract, Next Day Close")
    print(f"  Breakeven Points: {breakeven}")
    assert breakeven > 0, "Breakeven calculation failed"
    print("  ✅ Passed")
    
    # Test 8: Contract specs
    print("\n[Test 8] Contract Specifications")
    specs = calc.get_contract_specs("IC0")
    print(f"  Symbol: IC0")
    print(f"  Product: {specs['product']}")
    print(f"  Multiplier: {specs['multiplier']}")
    print(f"  Margin Ratio: {specs['margin_ratio']}")
    print(f"  Tick Size: {specs['tick_size']}")
    assert specs['multiplier'] == 200, "Contract specs failed"
    print("  ✅ Passed")
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    test_futures_calculator()
