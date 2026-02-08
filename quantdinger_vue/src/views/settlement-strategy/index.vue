<template>
  <div class="settlement-strategy-page">
    <a-page-header
      :title="$t('menu.settlement.title', '结算价套利策略')"
      :sub-title="$t('menu.settlement.subtitle', '股指期货结算价差套利 - 完整版')"
    >
      <template slot="extra">
        <a-space>
          <a-tag v-if="isTradingTime" color="green">交易时段</a-tag>
          <a-tag v-else color="grey">非交易时段</a-tag>
          <a-tag v-if="isWatchPeriod" color="orange">观察期 (14:30-15:00)</a-tag>
          <a-button
            v-if="!isRunning"
            type="primary"
            icon="play-circle"
            :loading="startLoading"
            @click="handleStart"
          >
            启动策略
          </a-button>
          <a-button
            v-else
            type="danger"
            icon="pause-circle"
            :loading="stopLoading"
            @click="handleStop"
          >
            停止策略
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-card :bordered="false">
      <a-tabs v-model="activeTab" @change="onTabChange">
        <a-tab-pane key="monitor" tab="实时监控">
          <monitor-panel
            ref="monitorPanel"
            :status="strategyStatus"
            :is-running="isRunning"
          />
        </a-tab-pane>

        <a-tab-pane key="positions" tab="持仓管理">
          <position-table :is-running="isRunning" />
        </a-tab-pane>

        <a-tab-pane key="config" tab="策略配置">
          <config-panel
            :is-running="isRunning"
            @config-saved="onConfigSaved"
          />
        </a-tab-pane>

        <a-tab-pane key="history" tab="交易历史">
          <trade-history />
        </a-tab-pane>

        <a-tab-pane key="pnl" tab="盈亏分析">
          <pnl-chart />
        </a-tab-pane>

        <a-tab-pane key="backtest" tab="历史回测">
          <backtest-panel />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script>
import { getStrategyStatus, startStrategy, stopStrategy } from '@/api/settlement-strategy'
import MonitorPanel from './components/MonitorPanel'
import ConfigPanel from './components/ConfigPanel'
import PositionTable from './components/PositionTable'
import TradeHistory from './components/TradeHistory'
import BacktestPanel from './components/BacktestPanel'
import PnlChart from './components/PnlChart'

export default {
  name: 'SettlementStrategy',
  components: {
    MonitorPanel,
    ConfigPanel,
    PositionTable,
    TradeHistory,
    BacktestPanel,
    PnlChart
  },
  data () {
    return {
      activeTab: 'monitor',
      isRunning: false,
      isTradingTime: false,
      isWatchPeriod: false,
      startLoading: false,
      stopLoading: false,
      strategyStatus: {},
      statusTimer: null
    }
  },
  mounted () {
    this.fetchStatus()
    this.startStatusPolling()
  },
  beforeDestroy () {
    this.stopStatusPolling()
  },
  methods: {
    async fetchStatus () {
      try {
        const res = await getStrategyStatus()
        if (res.success) {
          this.strategyStatus = res.data
          this.isRunning = res.data.is_running || false
          this.isTradingTime = res.data.is_trading_time || false
          this.isWatchPeriod = res.data.is_watch_period || false
        }
      } catch (e) {
        console.error('Failed to fetch status:', e)
      }
    },
    startStatusPolling () {
      this.statusTimer = setInterval(() => {
        this.fetchStatus()
      }, 5000) // Poll every 5 seconds
    },
    stopStatusPolling () {
      if (this.statusTimer) {
        clearInterval(this.statusTimer)
        this.statusTimer = null
      }
    },
    async handleStart () {
      this.startLoading = true
      try {
        const res = await startStrategy()
        if (res.success) {
          this.$message.success('策略启动成功')
          this.isRunning = true
          this.fetchStatus()
        } else {
          this.$message.error(res.message || '启动失败')
        }
      } catch (e) {
        this.$message.error('启动策略失败: ' + (e.message || '未知错误'))
      } finally {
        this.startLoading = false
      }
    },
    async handleStop () {
      this.stopLoading = true
      try {
        const res = await stopStrategy()
        if (res.success) {
          this.$message.success('策略已停止')
          this.isRunning = false
          this.fetchStatus()
        } else {
          this.$message.error(res.message || '停止失败')
        }
      } catch (e) {
        this.$message.error('停止策略失败: ' + (e.message || '未知错误'))
      } finally {
        this.stopLoading = false
      }
    },
    onTabChange (key) {
      this.activeTab = key
    },
    onConfigSaved () {
      this.fetchStatus()
    }
  }
}
</script>

<style lang="less" scoped>
.settlement-strategy-page {
  padding: 24px;

  .ant-page-header {
    padding: 0 0 16px 0;
  }
}
</style>
