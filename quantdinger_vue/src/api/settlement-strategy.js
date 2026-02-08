import request from '@/utils/request'

const baseUrl = '/api/settlement-strategy'

// ========== Strategy Control ==========

/**
 * Get strategy running status
 */
export function getStrategyStatus () {
  return request({
    url: `${baseUrl}/status`,
    method: 'get'
  })
}

/**
 * Start the strategy
 * @param {Object} config - Strategy configuration
 * @param {Array} config.symbols - Trading symbols, e.g. ["IM0", "IC0"]
 * @param {Number} config.threshold_1 - Level 1 entry threshold (default 0.01)
 * @param {Number} config.threshold_2 - Level 2 entry threshold (default 0.02)
 * @param {Number} config.alert_threshold - Alert threshold (default 0.008)
 * @param {Number} config.position_size_1 - Level 1 position size
 * @param {Number} config.position_size_2 - Level 2 position size
 * @param {Number} config.max_daily_loss - Max daily loss
 * @param {Number} config.max_drawdown - Max drawdown ratio
 */
export function startStrategy (config = {}) {
  return request({
    url: `${baseUrl}/start`,
    method: 'post',
    data: config
  })
}

/**
 * Stop the strategy
 */
export function stopStrategy () {
  return request({
    url: `${baseUrl}/stop`,
    method: 'post'
  })
}

/**
 * Get strategy configuration
 */
export function getStrategyConfig () {
  return request({
    url: `${baseUrl}/config`,
    method: 'get'
  })
}

/**
 * Update strategy configuration (hot-update)
 * @param {Object} config - Updated configuration fields
 */
export function updateStrategyConfig (config) {
  return request({
    url: `${baseUrl}/config`,
    method: 'put',
    data: config
  })
}

// ========== Monitoring ==========

/**
 * Get real-time monitoring data
 */
export function getMonitorData () {
  return request({
    url: `${baseUrl}/monitor`,
    method: 'get'
  })
}

/**
 * Get current open positions
 */
export function getPositions () {
  return request({
    url: `${baseUrl}/positions`,
    method: 'get'
  })
}

/**
 * Get today's signals
 */
export function getSignals () {
  return request({
    url: `${baseUrl}/signals`,
    method: 'get'
  })
}

// ========== History ==========

/**
 * Get trade history
 * @param {Object} params - Query parameters
 * @param {String} params.symbol - Filter by symbol
 * @param {String} params.start_date - Start date (YYYY-MM-DD)
 * @param {String} params.end_date - End date (YYYY-MM-DD)
 * @param {Number} params.page - Page number
 * @param {Number} params.page_size - Items per page
 */
export function getTrades (params = {}) {
  return request({
    url: `${baseUrl}/trades`,
    method: 'get',
    params
  })
}

/**
 * Get P&L summary
 */
export function getPnlSummary () {
  return request({
    url: `${baseUrl}/pnl`,
    method: 'get'
  })
}

/**
 * Get risk events
 * @param {Number} limit - Max events to return
 */
export function getRiskEvents (limit = 50) {
  return request({
    url: `${baseUrl}/risk-events`,
    method: 'get',
    params: { limit }
  })
}

// ========== Backtest ==========

/**
 * Run strategy backtest
 * @param {Object} params - Backtest parameters
 * @param {String} params.start_date - Start date (YYYY-MM-DD)
 * @param {String} params.end_date - End date (YYYY-MM-DD)
 * @param {Array} params.symbols - Symbols to backtest
 * @param {Number} params.threshold_1 - Entry threshold 1
 * @param {Number} params.threshold_2 - Entry threshold 2
 * @param {Number} params.initial_capital - Initial capital
 */
export function runBacktest (params) {
  return request({
    url: `${baseUrl}/backtest`,
    method: 'post',
    data: params
  })
}
