/**
 * CN Futures API
 * 中国股指期货 API 封装
 *
 * Endpoints:
 * - getContracts() - Get contract list / 获取合约列表
 * - getQuote(symbol) - Get real-time quote / 获取实时行情
 * - getKline(symbol, timeframe, limit) - Get K-line data / 获取K线数据
 * - calculateMargin(data) - Calculate margin / 计算保证金
 * - calculateFee(data) - Calculate fee / 计算手续费
 * - calculateTradeCost(data) - Calculate complete trade cost / 计算完整交易成本
 * - getStrategyStatus() - Get strategy status / 获取策略状态
 * - startStrategy(data) - Start strategy / 启动策略
 * - stopStrategy() - Stop strategy / 停止策略
 * - getStrategyConfig() - Get strategy config / 获取策略配置
 * - updateStrategyConfig(data) - Update strategy config / 更新策略配置
 * - getStrategyTrades(params) - Get trade records / 获取交易记录
 * - getStrategyPositions(status) - Get positions / 获取持仓
 * - getStrategyPnl(period) - Get P&L statistics / 获取盈亏统计
 * - getStrategySignals(params) - Get signal records / 获取信号记录
 */
import request from '@/utils/request'

const API_PREFIX = '/api/cn-futures'

// ==================== Basic Data ====================

/**
 * Get contract list
 * 获取合约列表
 * @returns {Promise} Contract list
 */
export function getContracts () {
  return request({
    url: `${API_PREFIX}/contracts`,
    method: 'get'
  })
}

/**
 * Get real-time quote
 * 获取实时行情
 * @param {string} symbol - Contract symbol (IC0, IM0, IF0, IH0)
 * @returns {Promise} Quote data
 */
export function getQuote (symbol) {
  return request({
    url: `${API_PREFIX}/quote`,
    method: 'get',
    params: { symbol }
  })
}

/**
 * Get K-line data
 * 获取K线数据
 * @param {string} symbol - Contract symbol
 * @param {string} timeframe - Time period (1m, 5m, 15m, 30m, 1H, 1D)
 * @param {number} limit - Number of bars (default 300, max 1000)
 * @param {number} beforeTime - Unix timestamp (optional)
 * @returns {Promise} K-line data list
 */
export function getKline (symbol, timeframe = '1D', limit = 300, beforeTime = null) {
  const params = { symbol, timeframe, limit }
  if (beforeTime) {
    params.before_time = beforeTime
  }
  return request({
    url: `${API_PREFIX}/kline`,
    method: 'get',
    params
  })
}

// ==================== Calculation ====================

/**
 * Calculate margin
 * 计算保证金
 * @param {Object} data - { symbol, price, quantity }
 * @returns {Promise} Margin calculation result
 */
export function calculateMargin (data) {
  return request({
    url: `${API_PREFIX}/calculate/margin`,
    method: 'post',
    data
  })
}

/**
 * Calculate fee
 * 计算手续费
 * @param {Object} data - { symbol, price, quantity, is_open, is_close_today }
 * @returns {Promise} Fee calculation result
 */
export function calculateFee (data) {
  return request({
    url: `${API_PREFIX}/calculate/fee`,
    method: 'post',
    data
  })
}

/**
 * Calculate complete trade cost
 * 计算完整交易成本
 * @param {Object} data - { symbol, entry_price, exit_price, quantity, is_same_day }
 * @returns {Promise} Trade cost calculation
 */
export function calculateTradeCost (data) {
  return request({
    url: `${API_PREFIX}/calculate/trade-cost`,
    method: 'post',
    data
  })
}

// ==================== Strategy Control ====================

/**
 * Get strategy status
 * 获取策略状态
 * @returns {Promise} Strategy status
 */
export function getStrategyStatus () {
  return request({
    url: `${API_PREFIX}/strategy/status`,
    method: 'get'
  })
}

/**
 * Start strategy
 * 启动策略
 * @param {Object} data - Optional config to save before starting
 * @returns {Promise} Start result
 */
export function startStrategy (data = {}) {
  return request({
    url: `${API_PREFIX}/strategy/start`,
    method: 'post',
    data
  })
}

/**
 * Stop strategy
 * 停止策略
 * @returns {Promise} Stop result
 */
export function stopStrategy () {
  return request({
    url: `${API_PREFIX}/strategy/stop`,
    method: 'post'
  })
}

/**
 * Get strategy configuration
 * 获取策略配置
 * @returns {Promise} Strategy configuration
 */
export function getStrategyConfig () {
  return request({
    url: `${API_PREFIX}/strategy/config`,
    method: 'get'
  })
}

/**
 * Update strategy configuration
 * 更新策略配置
 * @param {Object} data - Configuration fields to update
 * @returns {Promise} Update result
 */
export function updateStrategyConfig (data) {
  return request({
    url: `${API_PREFIX}/strategy/config`,
    method: 'put',
    data
  })
}

// ==================== Data Query ====================

/**
 * Get trade records
 * 获取交易记录
 * @param {Object} params - { limit, offset, symbol }
 * @returns {Promise} Trade records
 */
export function getStrategyTrades (params = {}) {
  return request({
    url: `${API_PREFIX}/strategy/trades`,
    method: 'get',
    params: {
      limit: params.limit || 50,
      offset: params.offset || 0,
      symbol: params.symbol
    }
  })
}

/**
 * Get positions
 * 获取持仓
 * @param {string} status - Position status (open/closed/all)
 * @returns {Promise} Positions list
 */
export function getStrategyPositions (status = 'open') {
  return request({
    url: `${API_PREFIX}/strategy/positions`,
    method: 'get',
    params: { status }
  })
}

/**
 * Get P&L statistics
 * 获取盈亏统计
 * @param {string} period - Time period (day/week/month/year)
 * @returns {Promise} P&L summary and history
 */
export function getStrategyPnl (period = 'month') {
  return request({
    url: `${API_PREFIX}/strategy/pnl`,
    method: 'get',
    params: { period }
  })
}

/**
 * Get signal records
 * 获取信号记录
 * @param {Object} params - { limit, symbol, executed }
 * @returns {Promise} Signal records
 */
export function getStrategySignals (params = {}) {
  return request({
    url: `${API_PREFIX}/strategy/signals`,
    method: 'get',
    params: {
      limit: params.limit || 50,
      symbol: params.symbol,
      executed: params.executed
    }
  })
}

// ==================== Batch Data Fetch ====================

/**
 * Get quotes for multiple symbols
 * 获取多个合约的行情
 * @param {string[]} symbols - Array of symbols
 * @returns {Promise} Object with symbol as key and quote as value
 */
export async function getMultipleQuotes (symbols) {
  const quotes = {}
  const promises = symbols.map(symbol =>
    getQuote(symbol)
      .then(res => {
        if (res.code === 1 && res.data) {
          quotes[symbol] = res.data
        }
      })
      .catch(() => {
        quotes[symbol] = null
      })
  )
  await Promise.all(promises)
  return quotes
}

// ==================== Default Export ====================

export default {
  getContracts,
  getQuote,
  getKline,
  calculateMargin,
  calculateFee,
  calculateTradeCost,
  getStrategyStatus,
  startStrategy,
  stopStrategy,
  getStrategyConfig,
  updateStrategyConfig,
  getStrategyTrades,
  getStrategyPositions,
  getStrategyPnl,
  getStrategySignals,
  getMultipleQuotes
}
