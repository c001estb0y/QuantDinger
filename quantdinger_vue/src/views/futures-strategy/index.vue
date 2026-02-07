<template>
  <div class="futures-strategy-container">
    <!-- Page Header -->
    <a-page-header
      :title="$t('menu.futures.title', '期货策略')"
      :sub-title="$t('menu.futures.subtitle', '中国股指期货跌幅套利策略')"
      style="padding: 0 0 16px 0"
    >
      <template #extra>
        <a-space>
          <a-tag :color="strategyStatus.is_running ? 'green' : 'default'">
            {{ strategyStatus.is_running ? $t('futures.status.running', '运行中') : $t('futures.status.stopped', '已停止') }}
          </a-tag>
<a-button
            v-if="!strategyStatus.is_running"
            type="primary"
            :loading="startLoading"
            @click="handleStartStrategy"
          >
            <a-icon type="play-circle" />
            {{ $t('futures.action.start', '启动策略') }}
          </a-button>
<a-button
            v-else
            type="primary"
            danger
            :loading="stopLoading"
            @click="handleStopStrategy"
          >
            <a-icon type="pause-circle" />
            {{ $t('futures.action.stop', '停止策略') }}
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <!-- Main Content -->
    <a-row :gutter="[16, 16]">
      <!-- Left Column: Contract Selector & Quote Panel -->
      <a-col :xs="24" :lg="16">
        <!-- Contract Selector -->
        <a-card size="small" :title="$t('futures.contracts', '合约选择')" style="margin-bottom: 16px">
<ContractSelector
            :selected-symbols="selectedSymbols"
            :contracts="contracts"
            @change="handleContractChange"
          />
        </a-card>

        <!-- Quote Panel -->
        <a-card size="small" :title="$t('futures.quotes', '实时行情')" style="margin-bottom: 16px">
          <QuotePanel
            :quotes="quotes"
            :selectedSymbols="selectedSymbols"
            :loading="quotesLoading"
          />
        </a-card>

        <!-- Position Table -->
        <a-card size="small" :title="$t('futures.positions', '当前持仓')" style="margin-bottom: 16px">
          <PositionTable
            :positions="positions"
            :quotes="quotes"
            :loading="positionsLoading"
          />
        </a-card>

        <!-- Trade History -->
        <a-card size="small" :title="$t('futures.trades', '交易记录')">
          <TradeHistory
            :trades="trades"
            :loading="tradesLoading"
            :pagination="tradesPagination"
            @page-change="handleTradesPageChange"
          />
        </a-card>
      </a-col>

      <!-- Right Column: Strategy Panel & PnL Chart -->
      <a-col :xs="24" :lg="8">
        <!-- Strategy Panel -->
        <a-card size="small" :title="$t('futures.strategyConfig', '策略配置')" style="margin-bottom: 16px">
          <StrategyPanel
            :config="strategyConfig"
            :status="strategyStatus"
            :loading="configLoading"
            @save="handleSaveConfig"
          />
        </a-card>

        <!-- PnL Chart -->
        <a-card size="small" :title="$t('futures.pnl', '盈亏统计')">
          <PnlChart
            :summary="pnlSummary"
            :history="pnlHistory"
            :loading="pnlLoading"
            :period="pnlPeriod"
            @period-change="handlePnlPeriodChange"
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'

import ContractSelector from './components/ContractSelector.vue'
import QuotePanel from './components/QuotePanel.vue'
import StrategyPanel from './components/StrategyPanel.vue'
import PositionTable from './components/PositionTable.vue'
import TradeHistory from './components/TradeHistory.vue'
import PnlChart from './components/PnlChart.vue'

import {
  getContracts,
  getStrategyStatus,
  startStrategy,
  stopStrategy,
  getStrategyConfig,
  updateStrategyConfig,
  getStrategyTrades,
  getStrategyPositions,
  getStrategyPnl,
  getMultipleQuotes
} from '@/api/cn_futures'

export default {
  name: 'FuturesStrategy',
  components: {
    ContractSelector,
    QuotePanel,
    StrategyPanel,
    PositionTable,
    TradeHistory,
    PnlChart
  },
  setup () {
    // ==================== State ====================

    // Contract data
    const contracts = ref([])
    const selectedSymbols = ref(['IC0', 'IM0', 'IF0', 'IH0'])

    // Quote data
    const quotes = ref({})
    const quotesLoading = ref(false)

    // Strategy status and config
    const strategyStatus = reactive({
      is_running: false,
      monitoring_start: '09:30',
      monitoring_end: '15:00',
      today_signal_count: 0,
      open_position_count: 0,
      positions_summary: []
    })

    const strategyConfig = reactive({
      symbols: ['IC0', 'IM0', 'IF0', 'IH0'],
      drop_threshold_1: -2.0,
      drop_threshold_2: -3.0,
      monitoring_start: '09:30',
      monitoring_end: '15:00',
      max_position: 1,
      notification_channels: ['browser'],
      telegram_chat_id: '',
      wechat_webhook: ''
    })

    const configLoading = ref(false)
    const startLoading = ref(false)
    const stopLoading = ref(false)

    // Positions
    const positions = ref([])
    const positionsLoading = ref(false)

    // Trades
    const trades = ref([])
    const tradesLoading = ref(false)
    const tradesPagination = reactive({
      current: 1,
      pageSize: 10,
      total: 0
    })

    // PnL
    const pnlSummary = reactive({
      total_pnl: 0,
      total_fee: 0,
      net_pnl: 0,
      trade_count: 0,
      win_count: 0,
      loss_count: 0,
      win_rate: 0
    })
    const pnlHistory = ref([])
    const pnlLoading = ref(false)
    const pnlPeriod = ref('month')

    // Refresh timer
    let refreshTimer = null

    // ==================== Data Loading ====================

    const loadContracts = async () => {
      try {
        const res = await getContracts()
        if (res.code === 1 && res.data) {
          contracts.value = res.data
        }
      } catch (error) {
        console.error('Failed to load contracts:', error)
      }
    }

    const loadQuotes = async () => {
      if (selectedSymbols.value.length === 0) {
        quotes.value = {}
        return
      }

      quotesLoading.value = true
      try {
        const result = await getMultipleQuotes(selectedSymbols.value)
        quotes.value = result
      } catch (error) {
        console.error('Failed to load quotes:', error)
      } finally {
        quotesLoading.value = false
      }
    }

    const loadStrategyStatus = async () => {
      try {
        const res = await getStrategyStatus()
        if (res.code === 1 && res.data) {
          Object.assign(strategyStatus, res.data)
        }
      } catch (error) {
        console.error('Failed to load strategy status:', error)
      }
    }

    const loadStrategyConfig = async () => {
      configLoading.value = true
      try {
        const res = await getStrategyConfig()
        if (res.code === 1 && res.data) {
          Object.assign(strategyConfig, res.data)
          // Sync selected symbols with config
          if (res.data.symbols) {
            selectedSymbols.value = res.data.symbols
          }
        }
      } catch (error) {
        console.error('Failed to load strategy config:', error)
      } finally {
        configLoading.value = false
      }
    }

    const loadPositions = async () => {
      positionsLoading.value = true
      try {
        const res = await getStrategyPositions('open')
        if (res.code === 1 && res.data) {
          positions.value = res.data
        }
      } catch (error) {
        console.error('Failed to load positions:', error)
      } finally {
        positionsLoading.value = false
      }
    }

    const loadTrades = async (page = 1) => {
      tradesLoading.value = true
      try {
        const res = await getStrategyTrades({
          limit: tradesPagination.pageSize,
          offset: (page - 1) * tradesPagination.pageSize
        })
        if (res.code === 1 && res.data) {
          trades.value = res.data.trades || []
          tradesPagination.total = res.data.total || trades.value.length
          tradesPagination.current = page
        }
      } catch (error) {
        console.error('Failed to load trades:', error)
      } finally {
        tradesLoading.value = false
      }
    }

    const loadPnl = async (period = 'month') => {
      pnlLoading.value = true
      try {
        const res = await getStrategyPnl(period)
        if (res.code === 1 && res.data) {
          if (res.data.summary) {
            Object.assign(pnlSummary, res.data.summary)
          }
          pnlHistory.value = res.data.history || []
        }
      } catch (error) {
        console.error('Failed to load pnl:', error)
      } finally {
        pnlLoading.value = false
      }
    }

    // ==================== Event Handlers ====================

    const handleContractChange = (symbols) => {
      selectedSymbols.value = symbols
      loadQuotes()
    }

    const handleStartStrategy = async () => {
      startLoading.value = true
      try {
        const res = await startStrategy({ config: strategyConfig })
        if (res.code === 1) {
          message.success('策略已启动')
          strategyStatus.is_running = true
        } else {
          message.error(res.msg || '启动失败')
        }
      } catch (error) {
        message.error('启动失败: ' + (error.message || '未知错误'))
      } finally {
        startLoading.value = false
      }
    }

    const handleStopStrategy = async () => {
      stopLoading.value = true
      try {
        const res = await stopStrategy()
        if (res.code === 1) {
          message.success('策略已停止')
          strategyStatus.is_running = false
        } else {
          message.error(res.msg || '停止失败')
        }
      } catch (error) {
        message.error('停止失败: ' + (error.message || '未知错误'))
      } finally {
        stopLoading.value = false
      }
    }

    const handleSaveConfig = async (config) => {
      configLoading.value = true
      try {
        Object.assign(strategyConfig, config)
        const res = await updateStrategyConfig(config)
        if (res.code === 1) {
          message.success('配置已保存')
        } else {
          message.error(res.msg || '保存失败')
        }
      } catch (error) {
        message.error('保存失败: ' + (error.message || '未知错误'))
      } finally {
        configLoading.value = false
      }
    }

    const handleTradesPageChange = (page) => {
      loadTrades(page)
    }

    const handlePnlPeriodChange = (period) => {
      pnlPeriod.value = period
      loadPnl(period)
    }

    // ==================== Auto Refresh ====================

    const startAutoRefresh = () => {
      // Refresh quotes every 5 seconds
      refreshTimer = setInterval(() => {
        loadQuotes()
        loadStrategyStatus()
      }, 5000)
    }

    const stopAutoRefresh = () => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
        refreshTimer = null
      }
    }

    // ==================== Lifecycle ====================

    onMounted(async () => {
      // Load initial data
      await Promise.all([
        loadContracts(),
        loadStrategyConfig(),
        loadStrategyStatus()
      ])

      // Load data that depends on config
      await Promise.all([
        loadQuotes(),
        loadPositions(),
        loadTrades(),
        loadPnl()
      ])

      // Start auto refresh
      startAutoRefresh()
    })

    onUnmounted(() => {
      stopAutoRefresh()
    })

    // ==================== Return ====================

    return {
      // State
      contracts,
      selectedSymbols,
      quotes,
      quotesLoading,
      strategyStatus,
      strategyConfig,
      configLoading,
      startLoading,
      stopLoading,
      positions,
      positionsLoading,
      trades,
      tradesLoading,
      tradesPagination,
      pnlSummary,
      pnlHistory,
      pnlLoading,
      pnlPeriod,

      // Methods
      handleContractChange,
      handleStartStrategy,
      handleStopStrategy,
      handleSaveConfig,
      handleTradesPageChange,
      handlePnlPeriodChange
    }
  }
}
</script>

<style lang="less" scoped>
.futures-strategy-container {
  padding: 16px;
  background-color: #f0f2f5;
  min-height: calc(100vh - 64px);
}

// Responsive adjustments
@media (max-width: 992px) {
  .futures-strategy-container {
    padding: 8px;
  }
}
</style>
