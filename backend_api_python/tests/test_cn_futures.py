"""
CN Futures API Test Suite
中国股指期货 API 测试套件

Tests for:
- Calculator functions (margin, fee, trade cost)
- Data source (contracts, quotes, kline)
- Strategy config CRUD
- Position and trade management
- API endpoints

Author: QuantDinger
Created: 2026-02-04
"""

import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFuturesCalculator(unittest.TestCase):
    """Test futures calculator functions"""
    
    def setUp(self):
        from app.services.futures_calculator import FuturesCalculator
        self.calc = FuturesCalculator()
    
    def test_margin_calculation_ic(self):
        """Test margin calculation for IC contract"""
        result = self.calc.margin.calculate('IC0', price=5500, quantity=1)
        
        # IC: multiplier=200, margin_ratio=12%
        expected_contract_value = 5500 * 200 * 1
        expected_margin = expected_contract_value * 0.12
        
        self.assertEqual(result.contract_value, expected_contract_value)
        self.assertAlmostEqual(result.margin_required, expected_margin, places=2)
        self.assertEqual(result.multiplier, 200)
        self.assertEqual(result.margin_ratio, 0.12)
        
        print(f"✅ IC Margin Test Passed: {result.margin_required:.2f}")
    
    def test_margin_calculation_if(self):
        """Test margin calculation for IF contract"""
        result = self.calc.margin.calculate('IF0', price=4000, quantity=2)
        
        # IF: multiplier=300, margin_ratio=10%
        expected_contract_value = 4000 * 300 * 2
        expected_margin = expected_contract_value * 0.10
        
        self.assertEqual(result.contract_value, expected_contract_value)
        self.assertAlmostEqual(result.margin_required, expected_margin, places=2)
        self.assertEqual(result.multiplier, 300)
        self.assertEqual(result.margin_ratio, 0.10)
        
        print(f"✅ IF Margin Test Passed: {result.margin_required:.2f}")
    
    def test_fee_calculation_open(self):
        """Test fee calculation for opening position"""
        result = self.calc.fee.calculate('IC0', price=5500, quantity=1, is_open=True)
        
        # IC: fee_rate_open = 0.000023
        expected_contract_value = 5500 * 200 * 1
        expected_fee = expected_contract_value * 0.000023
        
        self.assertEqual(result.contract_value, expected_contract_value)
        self.assertAlmostEqual(result.fee_amount, expected_fee, places=4)
        self.assertFalse(result.is_close_today)
        
        print(f"✅ Open Fee Test Passed: {result.fee_amount:.2f}")
    
    def test_fee_calculation_close_today(self):
        """Test fee calculation for closing today's position"""
        result = self.calc.fee.calculate(
            'IC0', price=5500, quantity=1,
            is_open=False, is_close_today=True
        )
        
        # IC: fee_rate_close_today = 0.000345 (15x normal)
        expected_contract_value = 5500 * 200 * 1
        expected_fee = expected_contract_value * 0.000345
        
        self.assertAlmostEqual(result.fee_amount, expected_fee, places=4)
        self.assertTrue(result.is_close_today)
        
        print(f"✅ Close Today Fee Test Passed: {result.fee_amount:.2f}")
    
    def test_round_trip_fee(self):
        """Test round trip (open + close) fee calculation"""
        result = self.calc.fee.calculate_round_trip(
            'IC0',
            entry_price=5500,
            exit_price=5550,
            quantity=1,
            is_same_day=False
        )
        
        self.assertIn('open', result)
        self.assertIn('close', result)
        self.assertIn('total', result)
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['total'], result['open'].fee_amount + result['close'].fee_amount)
        
        print(f"✅ Round Trip Fee Test Passed: {result['total']:.2f}")
    
    def test_trade_cost_calculation(self):
        """Test complete trade cost calculation"""
        result = self.calc.calculate_trade_cost(
            symbol='IC0',
            entry_price=5500,
            exit_price=5550,
            quantity=1,
            is_same_day=False
        )
        
        # 50 points profit * 200 multiplier = 10000 gross
        expected_gross_pnl = 50 * 200 * 1
        
        self.assertIn('margin_required', result)
        self.assertIn('fee_total', result)
        self.assertIn('gross_pnl', result)
        self.assertIn('net_pnl', result)
        self.assertEqual(result['gross_pnl'], expected_gross_pnl)
        self.assertLess(result['net_pnl'], result['gross_pnl'])  # Net < Gross due to fees
        
        print(f"✅ Trade Cost Test Passed: Gross={result['gross_pnl']:.2f}, Net={result['net_pnl']:.2f}")
    
    def test_breakeven_points(self):
        """Test breakeven points calculation"""
        result = self.calc.calculate_breakeven_points(
            'IC0',
            entry_price=5500,
            quantity=1,
            is_same_day=False
        )
        
        self.assertGreater(result, 0)
        self.assertLess(result, 10)  # Should be a few points
        
        print(f"✅ Breakeven Points Test Passed: {result:.2f} points")
    
    def test_price_limit_check(self):
        """Test price limit checking"""
        result = self.calc.price_limit.check(
            'IC0',
            current_price=6000,
            prev_settlement=5500
        )
        
        # 10% limit: upper=6050, lower=4950
        self.assertEqual(result.upper_limit, 6050.0)
        self.assertEqual(result.lower_limit, 4950.0)
        
        print(f"✅ Price Limit Test Passed: Upper={result.upper_limit}, Lower={result.lower_limit}")
    
    def test_contract_specs(self):
        """Test contract specifications retrieval"""
        specs = self.calc.get_contract_specs('IC0')
        
        self.assertEqual(specs['product'], 'IC')
        self.assertEqual(specs['multiplier'], 200)
        self.assertEqual(specs['margin_ratio'], 0.12)
        self.assertEqual(specs['tick_size'], 0.2)
        
        print(f"✅ Contract Specs Test Passed: {specs}")


class TestFuturesModels(unittest.TestCase):
    """Test futures database models (with mocking)"""
    
    @patch('app.models.futures.get_db_connection')
    def test_strategy_config_get(self, mock_db):
        """Test getting strategy config"""
        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            1, 1, '["IC0","IM0"]', -2.0, -3.0,
            '09:30', '15:00', 1, '["browser"]',
            '', '', False, datetime.now(), datetime.now()
        )
        mock_cursor.description = [
            ('id',), ('user_id',), ('symbols',), ('drop_threshold_1',),
            ('drop_threshold_2',), ('monitoring_start',), ('monitoring_end',),
            ('max_position',), ('notification_channels',), ('telegram_chat_id',),
            ('wechat_webhook',), ('is_running',), ('created_at',), ('updated_at',)
        ]
        mock_db.return_value.cursor.return_value = mock_cursor
        
        from app.models.futures import FuturesStrategyConfig
        
        config = FuturesStrategyConfig.get_config(1)
        
        self.assertIsNotNone(config)
        self.assertEqual(config['user_id'], 1)
        
        print("✅ Strategy Config Get Test Passed")
    
    @patch('app.models.futures.get_db_connection')
    def test_position_add(self, mock_db):
        """Test adding a position"""
        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (123,)  # Return new ID
        mock_db.return_value.cursor.return_value = mock_cursor
        
        from app.models.futures import FuturesPosition
        
        position_id = FuturesPosition.add_position(1, {
            'symbol': 'IC0',
            'direction': 'long',
            'quantity': 1,
            'entry_price': 5500
        })
        
        self.assertEqual(position_id, 123)
        
        print("✅ Position Add Test Passed")
    
    @patch('app.models.futures.get_db_connection')
    def test_trade_add(self, mock_db):
        """Test adding a trade"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (456,)
        mock_db.return_value.cursor.return_value = mock_cursor
        
        from app.models.futures import FuturesTrade
        
        trade_id = FuturesTrade.add_trade(1, {
            'symbol': 'IC0',
            'trade_type': 'open_long',
            'price': 5500,
            'quantity': 1,
            'fee': 25.3
        })
        
        self.assertEqual(trade_id, 456)
        
        print("✅ Trade Add Test Passed")


class TestFuturesDataSource(unittest.TestCase):
    """Test futures data source (with mocking)"""
    
    def test_parse_symbol(self):
        """Test symbol parsing"""
        from app.data_sources.cn_futures import CNFuturesDataSource
        
        ds = CNFuturesDataSource()
        
        # Test main contract
        product, code, is_main = ds._parse_symbol('IC0')
        self.assertEqual(product, 'IC')
        self.assertTrue(is_main)
        
        # Test specific contract
        product, code, is_main = ds._parse_symbol('IC2503')
        self.assertEqual(product, 'IC')
        self.assertFalse(is_main)
        
        print("✅ Symbol Parse Test Passed")
    
    def test_contract_info(self):
        """Test contract info retrieval"""
        from app.data_sources.cn_futures import CNFuturesDataSource
        
        ds = CNFuturesDataSource()
        
        with patch.object(ds, 'get_main_contract_code', return_value='IC2503'):
            info = ds.get_contract_info('IC0')
            
            self.assertEqual(info['product'], 'IC')
            self.assertEqual(info['multiplier'], 200)
            self.assertEqual(info['margin_ratio'], 0.12)
            self.assertTrue(info['is_main'])
        
        print("✅ Contract Info Test Passed")


class TestFuturesAPI(unittest.TestCase):
    """Test futures API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        from app import create_app
        
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Mock authentication
        self.auth_patcher = patch('app.utils.auth.login_required', lambda f: f)
        self.user_patcher = patch('app.utils.auth.get_current_user_id', return_value=1)
        self.auth_patcher.start()
        self.user_patcher.start()
    
    def tearDown(self):
        """Clean up"""
        self.auth_patcher.stop()
        self.user_patcher.stop()
    
    def test_calculate_margin_endpoint(self):
        """Test margin calculation endpoint"""
        response = self.client.post(
            '/api/cn-futures/calculate/margin',
            json={
                'symbol': 'IC0',
                'price': 5500,
                'quantity': 1
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['code'], 1)
        self.assertIn('data', data)
        self.assertIn('margin_required', data['data'])
        
        print(f"✅ Margin Endpoint Test Passed: {data['data']['margin_required']}")
    
    def test_calculate_fee_endpoint(self):
        """Test fee calculation endpoint"""
        response = self.client.post(
            '/api/cn-futures/calculate/fee',
            json={
                'symbol': 'IC0',
                'price': 5500,
                'quantity': 1,
                'is_open': True
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['code'], 1)
        self.assertIn('fee_amount', data['data'])
        
        print(f"✅ Fee Endpoint Test Passed: {data['data']['fee_amount']}")
    
    def test_calculate_trade_cost_endpoint(self):
        """Test trade cost calculation endpoint"""
        response = self.client.post(
            '/api/cn-futures/calculate/trade-cost',
            json={
                'symbol': 'IC0',
                'entry_price': 5500,
                'exit_price': 5550,
                'quantity': 1,
                'is_same_day': False
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['code'], 1)
        self.assertIn('gross_pnl', data['data'])
        self.assertIn('net_pnl', data['data'])
        
        print(f"✅ Trade Cost Endpoint Test Passed: Net PnL={data['data']['net_pnl']}")
    
    @patch('app.routes.cn_futures.get_data_source')
    def test_contracts_endpoint(self, mock_ds):
        """Test contracts list endpoint"""
        mock_instance = MagicMock()
        mock_instance.PRODUCTS = {
            'IC': {'name': '中证500', 'multiplier': 200, 'margin_ratio': 0.12, 'tick_size': 0.2},
            'IM': {'name': '中证1000', 'multiplier': 200, 'margin_ratio': 0.12, 'tick_size': 0.2},
            'IF': {'name': '沪深300', 'multiplier': 300, 'margin_ratio': 0.10, 'tick_size': 0.2},
            'IH': {'name': '上证50', 'multiplier': 300, 'margin_ratio': 0.10, 'tick_size': 0.2}
        }
        mock_instance.get_main_contract_code.return_value = 'IC2503'
        mock_ds.return_value = mock_instance
        
        response = self.client.get('/api/cn-futures/contracts')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['code'], 1)
        self.assertIsInstance(data['data'], list)
        self.assertGreater(len(data['data']), 0)
        
        print(f"✅ Contracts Endpoint Test Passed: {len(data['data'])} contracts")


class TestFuturesIntegration(unittest.TestCase):
    """Integration tests for futures functionality"""
    
    def test_full_trade_calculation_flow(self):
        """Test complete trade calculation flow"""
        from app.services.futures_calculator import FuturesCalculator
        
        calc = FuturesCalculator()
        
        # Simulate a trade
        entry_price = 5500
        exit_price = 5550
        quantity = 1
        symbol = 'IC0'
        
        # Step 1: Calculate margin needed
        margin = calc.margin.calculate(symbol, entry_price, quantity)
        print(f"  Margin required: {margin.margin_required:.2f}")
        
        # Step 2: Calculate entry fee
        entry_fee = calc.fee.calculate(symbol, entry_price, quantity, is_open=True)
        print(f"  Entry fee: {entry_fee.fee_amount:.2f}")
        
        # Step 3: Calculate exit fee (next day close)
        exit_fee = calc.fee.calculate(symbol, exit_price, quantity, is_open=False, is_close_today=False)
        print(f"  Exit fee: {exit_fee.fee_amount:.2f}")
        
        # Step 4: Calculate P&L
        cost = calc.calculate_trade_cost(symbol, entry_price, exit_price, quantity, is_same_day=False)
        print(f"  Gross P&L: {cost['gross_pnl']:.2f}")
        print(f"  Net P&L: {cost['net_pnl']:.2f}")
        
        # Verify
        self.assertGreater(cost['gross_pnl'], 0)  # 50 points profit
        self.assertEqual(cost['gross_pnl'], 50 * 200)  # 10,000 gross
        self.assertLess(cost['net_pnl'], cost['gross_pnl'])  # Fees deducted
        
        print("✅ Full Trade Flow Integration Test Passed")
    
    def test_price_limit_scenarios(self):
        """Test various price limit scenarios"""
        from app.services.futures_calculator import FuturesCalculator
        
        calc = FuturesCalculator()
        prev_settlement = 5500
        
        # Normal price
        normal = calc.price_limit.check('IC0', 5600, prev_settlement)
        self.assertEqual(normal.status.value, 'normal')
        
        # At upper limit
        at_upper = calc.price_limit.check('IC0', 6050, prev_settlement)
        self.assertEqual(at_upper.status.value, 'limit_up')
        
        # At lower limit
        at_lower = calc.price_limit.check('IC0', 4950, prev_settlement)
        self.assertEqual(at_lower.status.value, 'limit_down')
        
        # Near limit check
        is_near, direction = calc.price_limit.is_near_limit('IC0', 6000, prev_settlement, threshold=0.02)
        self.assertTrue(is_near)
        self.assertEqual(direction, 'up')
        
        print("✅ Price Limit Scenarios Test Passed")


def run_all_tests():
    """Run all test suites"""
    print("=" * 60)
    print("CN Futures API Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFuturesCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestFuturesModels))
    suite.addTests(loader.loadTestsFromTestCase(TestFuturesDataSource))
    suite.addTests(loader.loadTestsFromTestCase(TestFuturesIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    return result.wasSuccessful()


def run_api_tests():
    """Run only API endpoint tests (requires running app)"""
    print("=" * 60)
    print("CN Futures API Endpoint Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestFuturesAPI))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Run calculator and model tests (no database required)
    success = run_all_tests()
    
    # Uncomment to run API tests (requires app context)
    # success = run_api_tests()
    
    sys.exit(0 if success else 1)
