"""
中国股指期货数据源
支持 IC(中证500)、IM(中证1000)、IF(沪深300)、IH(上证50) 主力合约
使用 akshare 获取数据
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time

from app.data_sources.base import BaseDataSource, TIMEFRAME_SECONDS
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("akshare not installed, CNFuturesDataSource will not work")


class CNFuturesDataSource(BaseDataSource):
    """
    中国股指期货数据源
    支持 IC(中证500)、IM(中证1000)、IF(沪深300)、IH(上证50) 主力合约
    """
    
    name: str = "cn_futures"
    
    # 品种配置
    PRODUCTS = {
        'IC': {
            'name': '中证500股指期货',
            'multiplier': 200,      # 合约乘数：每点200元
            'margin_ratio': 0.12,   # 保证金比例：12%
            'tick_size': 0.2,       # 最小变动价位
        },
        'IM': {
            'name': '中证1000股指期货',
            'multiplier': 200,
            'margin_ratio': 0.12,
            'tick_size': 0.2,
        },
        'IF': {
            'name': '沪深300股指期货',
            'multiplier': 300,      # 每点300元
            'margin_ratio': 0.10,   # 10%
            'tick_size': 0.2,
        },
        'IH': {
            'name': '上证50股指期货',
            'multiplier': 300,
            'margin_ratio': 0.10,
            'tick_size': 0.2,
        },
    }
    
    # 时间周期映射到 akshare 的 period 参数
    TIMEFRAME_MAP = {
        '1m': '1',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1H': '60',
        '1D': 'daily',
    }
    
    def __init__(self):
        """Initialize CNFuturesDataSource"""
        if not AKSHARE_AVAILABLE:
            logger.error("akshare is required for CNFuturesDataSource")
        self._main_contract_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 3600  # 缓存1小时
    
    def _parse_symbol(self, symbol: str) -> tuple:
        """
        Parse symbol into product and contract code
        
        Args:
            symbol: e.g., "IC0", "IC2503", "IM0"
            
        Returns:
            (product, contract_code, is_main)
            e.g., ("IC", "IC2503", True) for "IC0"
        """
        symbol = symbol.upper()
        
        # Extract product code (first 2 letters)
        if len(symbol) < 2:
            raise ValueError(f"Invalid symbol: {symbol}")
        
        product = symbol[:2]
        if product not in self.PRODUCTS:
            raise ValueError(f"Unsupported product: {product}. Supported: {list(self.PRODUCTS.keys())}")
        
        # Check if it's main contract (ends with 0)
        is_main = symbol.endswith('0') and len(symbol) == 3
        
        if is_main:
            # Get actual main contract code
            contract_code = self.get_main_contract_code(product)
        else:
            contract_code = symbol
        
        return product, contract_code, is_main
    
    def get_main_contract_code(self, product: str) -> str:
        """
        Get current main contract code for a product
        
        Args:
            product: Product code (IC, IM, IF, IH)
            
        Returns:
            Main contract code, e.g., "IC2503"
        """
        if not AKSHARE_AVAILABLE:
            raise RuntimeError("akshare not available")
        
        product = product.upper()
        if product not in self.PRODUCTS:
            raise ValueError(f"Unsupported product: {product}")
        
        # Check cache
        cache_key = f"main_{product}"
        now = time.time()
        if cache_key in self._main_contract_cache:
            if now - self._cache_time.get(cache_key, 0) < self._cache_ttl:
                return self._main_contract_cache[cache_key]['code']
        
        try:
            # Use akshare to get futures list and find main contract
            # 获取金融期货合约信息
            df = ak.futures_zh_realtime(symbol=product)
            
            if df is not None and not df.empty:
                # Find the main contract (usually with highest volume or specific naming)
                # Main contract typically has '0' suffix in display or highest open interest
                
                # Try to find by symbol pattern
                for idx, row in df.iterrows():
                    sym = str(row.get('symbol', row.get('代码', '')))
                    if sym.upper().startswith(product):
                        # Check if this looks like a main contract
                        # Usually we look for the nearest month with high volume
                        main_code = sym.upper()
                        self._main_contract_cache[cache_key] = {'code': main_code}
                        self._cache_time[cache_key] = now
                        return main_code
                
                # If no specific main found, use first one
                first_row = df.iloc[0]
                main_code = str(first_row.get('symbol', first_row.get('代码', f'{product}0000')))
                self._main_contract_cache[cache_key] = {'code': main_code.upper()}
                self._cache_time[cache_key] = now
                return main_code.upper()
            
        except Exception as e:
            logger.warning(f"Failed to get main contract for {product}: {e}")
        
        # Fallback: estimate based on current date
        now_dt = datetime.now()
        # Stock index futures expire on third Friday of contract month
        # Main contract is usually current or next month
        month = now_dt.month
        year = now_dt.year % 100  # Get last 2 digits
        
        # If past 15th, likely next month is main
        if now_dt.day > 15:
            month += 1
            if month > 12:
                month = 1
                year += 1
        
        fallback_code = f"{product}{year:02d}{month:02d}"
        self._main_contract_cache[cache_key] = {'code': fallback_code}
        self._cache_time[cache_key] = now
        return fallback_code
    
    def get_contract_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get contract information
        
        Args:
            symbol: Contract code (IC0, IC2503, etc.)
            
        Returns:
            Contract information dict
        """
        product, contract_code, is_main = self._parse_symbol(symbol)
        product_info = self.PRODUCTS[product]
        
        return {
            "symbol": contract_code,
            "product": product,
            "name": f"{product_info['name']}{contract_code[2:]}",
            "multiplier": product_info['multiplier'],
            "margin_ratio": product_info['margin_ratio'],
            "tick_size": product_info['tick_size'],
            "is_main": is_main
        }
    
    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get K-line data for futures contract
        
        Args:
            symbol: Contract code (IC0, IM0, IF0, IH0 or specific like IC2503)
            timeframe: Time period (1m, 5m, 15m, 30m, 1H, 1D)
            limit: Number of bars (max 1000)
            before_time: Unix timestamp (seconds), get data before this time
            
        Returns:
            List of K-line data
        """
        if not AKSHARE_AVAILABLE:
            logger.error("akshare not available")
            return []
        
        try:
            product, contract_code, is_main = self._parse_symbol(symbol)
            
            # Map timeframe
            period = self.TIMEFRAME_MAP.get(timeframe)
            if not period:
                logger.warning(f"Unsupported timeframe: {timeframe}, using 1m")
                period = '1'
            
            # Get K-line data using akshare
            klines = self._fetch_klines_akshare(contract_code, period, limit, before_time)
            
            # Log result
            self.log_result(symbol, klines, timeframe)
            
            return klines
            
        except Exception as e:
            logger.error(f"Failed to get kline for {symbol}: {e}")
            return []
    
    def _fetch_klines_akshare(
        self,
        contract_code: str,
        period: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch K-lines using akshare
        
        Args:
            contract_code: Full contract code (e.g., IC2503)
            period: akshare period parameter
            limit: Number of bars
            before_time: Filter time
            
        Returns:
            Formatted K-line list
        """
        klines = []
        
        try:
            if period == 'daily':
                # Daily K-lines
                df = ak.futures_zh_daily_sina(symbol=contract_code)
            else:
                # Intraday K-lines (1, 5, 15, 30, 60 minutes)
                df = ak.futures_zh_minute_sina(symbol=contract_code, period=period)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {contract_code}")
                return []
            
            # Convert DataFrame to list of dicts
            for idx, row in df.iterrows():
                try:
                    # Parse timestamp
                    if 'datetime' in df.columns:
                        ts = self._parse_datetime(row['datetime'])
                    elif 'date' in df.columns:
                        ts = self._parse_datetime(row['date'])
                    elif '日期' in df.columns:
                        ts = self._parse_datetime(row['日期'])
                    else:
                        # Use index if it's datetime
                        ts = self._parse_datetime(idx)
                    
                    # Get OHLCV
                    open_price = float(row.get('open', row.get('开盘价', row.get('开盘', 0))))
                    high = float(row.get('high', row.get('最高价', row.get('最高', 0))))
                    low = float(row.get('low', row.get('最低价', row.get('最低', 0))))
                    close = float(row.get('close', row.get('收盘价', row.get('收盘', 0))))
                    volume = float(row.get('volume', row.get('成交量', row.get('成交', 0))))
                    
                    if ts and open_price > 0:
                        klines.append(self.format_kline(ts, open_price, high, low, close, volume))
                        
                except Exception as e:
                    logger.debug(f"Skip row due to parse error: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"akshare fetch error: {e}")
            # Try alternative method
            klines = self._fetch_klines_alternative(contract_code, period, limit)
        
        # Filter and limit
        klines = self.filter_and_limit(klines, limit, before_time)
        
        return klines
    
    def _fetch_klines_alternative(
        self,
        contract_code: str,
        period: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Alternative method to fetch K-lines if primary method fails
        
        Uses futures_main_sina for main contract data
        """
        klines = []
        
        try:
            # Extract product code
            product = contract_code[:2].upper()
            
            # Try getting main contract data
            if period == 'daily':
                df = ak.futures_main_sina(symbol=f"{product}0", start_date="20240101")
            else:
                # For intraday, try real-time data
                df = ak.futures_zh_realtime(symbol=product)
                
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    try:
                        ts = self._parse_datetime(row.get('日期', row.get('datetime', idx)))
                        open_price = float(row.get('开盘价', row.get('open', 0)))
                        high = float(row.get('最高价', row.get('high', 0)))
                        low = float(row.get('最低价', row.get('low', 0)))
                        close = float(row.get('收盘价', row.get('close', 0)))
                        volume = float(row.get('成交量', row.get('volume', 0)))
                        
                        if ts and open_price > 0:
                            klines.append(self.format_kline(ts, open_price, high, low, close, volume))
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Alternative fetch also failed: {e}")
        
        return klines
    
    def _parse_datetime(self, dt_value) -> Optional[int]:
        """
        Parse various datetime formats to Unix timestamp
        
        Args:
            dt_value: datetime string, datetime object, or pandas Timestamp
            
        Returns:
            Unix timestamp in seconds, or None if parse fails
        """
        if dt_value is None:
            return None
        
        try:
            # If already a timestamp
            if isinstance(dt_value, (int, float)):
                return int(dt_value)
            
            # If pandas Timestamp
            if hasattr(dt_value, 'timestamp'):
                return int(dt_value.timestamp())
            
            # If datetime object
            if isinstance(dt_value, datetime):
                return int(dt_value.timestamp())
            
            # Parse string
            dt_str = str(dt_value)
            
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d',
                '%Y%m%d',
                '%Y%m%d%H%M%S',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    return int(dt.timestamp())
                except ValueError:
                    continue
            
            logger.debug(f"Could not parse datetime: {dt_value}")
            return None
            
        except Exception as e:
            logger.debug(f"Datetime parse error: {e}")
            return None
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest ticker/quote for a futures contract
        
        Args:
            symbol: Contract code
            
        Returns:
            Ticker data dict
        """
        if not AKSHARE_AVAILABLE:
            raise RuntimeError("akshare not available")
        
        try:
            product, contract_code, is_main = self._parse_symbol(symbol)
            
            # Get real-time quote
            df = ak.futures_zh_realtime(symbol=product)
            
            if df is not None and not df.empty:
                # Find matching contract
                for idx, row in df.iterrows():
                    sym = str(row.get('symbol', row.get('代码', ''))).upper()
                    if sym == contract_code or (is_main and sym.startswith(product)):
                        last = float(row.get('current_price', row.get('最新价', row.get('close', 0))))
                        bid = float(row.get('bid', row.get('买价', last)))
                        ask = float(row.get('ask', row.get('卖价', last)))
                        volume = float(row.get('volume', row.get('成交量', 0)))
                        
                        return {
                            'symbol': sym,
                            'last': last,
                            'bid': bid,
                            'ask': ask,
                            'volume': volume,
                            'timestamp': int(time.time())
                        }
            
            # Fallback: return empty ticker
            return {
                'symbol': symbol,
                'last': 0,
                'bid': 0,
                'ask': 0,
                'volume': 0,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return {
                'symbol': symbol,
                'last': 0,
                'error': str(e),
                'timestamp': int(time.time())
            }
    
    def get_settlement_price(self, symbol: str, date: Optional[str] = None) -> Optional[float]:
        """
        Get settlement price for a contract
        
        Args:
            symbol: Contract code
            date: Date string (YYYY-MM-DD), None for latest
            
        Returns:
            Settlement price or None
        """
        try:
            product, contract_code, _ = self._parse_symbol(symbol)
            
            # Get daily data which includes settlement price
            df = ak.futures_zh_daily_sina(symbol=contract_code)
            
            if df is not None and not df.empty:
                if date:
                    # Filter by date
                    df['date_str'] = df['date'].astype(str)
                    row = df[df['date_str'].str.contains(date)]
                    if not row.empty:
                        return float(row.iloc[-1].get('settle', row.iloc[-1].get('结算价', 0)))
                else:
                    # Latest settlement
                    return float(df.iloc[-1].get('settle', df.iloc[-1].get('结算价', 0)))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get settlement price: {e}")
            return None
