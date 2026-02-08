<template>
  <div class="monitor-panel">
    <!-- Strategy Status Banner -->
    <a-row :gutter="16" class="status-banner">
      <a-col :span="24">
        <a-alert
          v-if="isRunning"
          type="success"
          :message="`🟢 策略运行中 | ${currentTime}`"
          banner
        />
        <a-alert
          v-else
          type="info"
          message="⚪ 策略未运行"
          banner
        />
      </a-col>
    </a-row>

    <!-- Statistics Cards -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :span="6">
        <a-statistic title="今日信号" :value="totalSignals" style="text-align: center;">
          <template slot="prefix"><a-icon type="bell" /></template>
        </a-statistic>
      </a-col>
      <a-col :span="6">
        <a-statistic title="持仓数" :value="openPositions" style="text-align: center;">
          <template slot="prefix"><a-icon type="wallet" /></template>
        </a-statistic>
      </a-col>
      <a-col :span="6">
        <a-statistic title="今日盈亏" :precision="2" style="text-align: center;">
          <template slot="prefix"><a-icon type="dollar" /></template>
          <span :class="dailyPnl >= 0 ? 'text-profit' : 'text-loss'">
            {{ dailyPnl >= 0 ? '+' : '' }}{{ dailyPnl.toFixed(2) }}
          </span>
        </a-statistic>
      </a-col>
      <a-col :span="6">
        <a-statistic title="占用保证金" :value="marginUsed" :precision="0" suffix="元" style="text-align: center;">
          <template slot="prefix"><a-icon type="bank" /></template>
        </a-statistic>
      </a-col>
    </a-row>

    <!-- Symbol Monitor Cards -->
    <a-row :gutter="16" style="margin-top: 24px;">
      <a-col :span="6" v-for="symbol in symbols" :key="symbol.code">
        <a-card
          :bordered="true"
          class="symbol-card"
          :class="{
            'card-triggered': symbol.triggered,
            'card-watching': symbol.watching && !symbol.triggered
          }"
        >
          <template slot="title">
            <span class="symbol-title">{{ symbol.code }}</span>
            <a-tag v-if="symbol.triggered" color="red" size="small" style="margin-left: 8px;">已触发</a-tag>
            <a-tag v-else-if="symbol.watching" color="orange" size="small" style="margin-left: 8px;">观察中</a-tag>
            <a-tag v-else color="default" size="small" style="margin-left: 8px;">待机</a-tag>
          </template>
          <div class="symbol-info">
            <div class="info-row">
              <span class="label">14:30价</span>
              <span class="value">{{ symbol.basePrice ? symbol.basePrice.toFixed(1) : '--' }}</span>
            </div>
            <div class="info-row">
              <span class="label">现价</span>
              <span class="value" :class="symbol.dropPct < 0 ? 'text-loss' : 'text-profit'">
                {{ symbol.currentPrice ? symbol.currentPrice.toFixed(1) : '--' }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">跌幅</span>
              <span
                class="value drop-pct"
                :class="getDropClass(symbol.dropPct)"
              >
                {{ symbol.dropPct !== null ? (symbol.dropPct * 100).toFixed(2) + '%' : '--' }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">VWAP</span>
              <span class="value">{{ symbol.vwap ? symbol.vwap.toFixed(1) : '--' }}</span>
            </div>
            <div class="info-row">
              <span class="label">状态</span>
              <span class="value">{{ symbol.stateLabel }}</span>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Today's Signals -->
    <a-card title="📋 今日信号" style="margin-top: 16px;" size="small">
      <a-table
        :columns="signalColumns"
        :data-source="todaySignals"
        :pagination="false"
        size="small"
        :locale="{ emptyText: '暂无信号' }"
        row-key="timestamp"
      />
    </a-card>
  </div>
</template>

<script>
import { getMonitorData, getSignals } from '@/api/settlement-strategy'

const STATE_LABELS = {
  'idle': '待机',
  'watching': '观察中',
  'position_1': '持仓L1',
  'position_2': '持仓L2',
  'closing': '平仓中'
}

const signalColumns = [
  {
    title: '时间',
    dataIndex: 'timestamp',
    key: 'timestamp',
    width: 180
  },
  {
    title: '类型',
    dataIndex: 'signal_type',
    key: 'signal_type',
    width: 120,
    customRender: (text) => {
      const map = {
        'buy_level_1': '🟢 买入L1',
        'buy_level_2': '🟡 买入L2',
        'sell_close': '🔴 平仓',
        'alert': '⚠️ 预警'
      }
      return map[text] || text
    }
  },
  {
    title: '合约',
    dataIndex: 'symbol',
    key: 'symbol',
    width: 80
  },
  {
    title: '价格',
    dataIndex: 'price',
    key: 'price',
    width: 100
  },
  {
    title: '基准价',
    dataIndex: 'base_price',
    key: 'base_price',
    width: 100
  },
  {
    title: '跌幅',
    dataIndex: 'drop_pct',
    key: 'drop_pct',
    width: 100,
    customRender: (text) => text ? (text * 100).toFixed(2) + '%' : '--'
  },
  {
    title: '数量',
    dataIndex: 'quantity',
    key: 'quantity',
    width: 60
  }
]

export default {
  name: 'MonitorPanel',
  props: {
    status: {
      type: Object,
      default: () => ({})
    },
    isRunning: {
      type: Boolean,
      default: false
    }
  },
  data () {
    return {
      currentTime: '',
      symbols: [],
      todaySignals: [],
      signalColumns,
      totalSignals: 0,
      openPositions: 0,
      dailyPnl: 0,
      marginUsed: 0,
      timeTimer: null,
      dataTimer: null
    }
  },
  mounted () {
    this.updateTime()
    this.timeTimer = setInterval(this.updateTime, 1000)
    this.fetchData()
    this.dataTimer = setInterval(this.fetchData, 5000)
  },
  beforeDestroy () {
    clearInterval(this.timeTimer)
    clearInterval(this.dataTimer)
  },
  methods: {
    updateTime () {
      this.currentTime = new Date().toLocaleString('zh-CN')
    },
    async fetchData () {
      try {
        const [monitorRes, signalRes] = await Promise.all([
          getMonitorData(),
          getSignals()
        ])

        if (monitorRes.success && monitorRes.data) {
          this.processMonitorData(monitorRes.data)
        }

        if (signalRes.success && signalRes.data) {
          this.todaySignals = signalRes.data.signals || []
          this.totalSignals = signalRes.data.count || 0
        }
      } catch (e) {
        console.error('Monitor fetch error:', e)
      }
    },
    processMonitorData (data) {
      const symbolsData = data.symbols || {}
      const positions = data.positions || {}

      this.openPositions = positions.open_count || 0
      this.marginUsed = positions.margin_used || 0
      this.dailyPnl = (data.risk && data.risk.daily_pnl) || 0

      const allSymbols = ['IM0', 'IC0', 'IF0', 'IH0']
      this.symbols = allSymbols.map(code => {
        const sd = symbolsData[code] || {}
        const rt = sd.realtime || {}
        const basePrice = sd.base_price || null
        const currentPrice = rt.last || null
        let dropPct = null
        if (basePrice && currentPrice) {
          dropPct = (currentPrice - basePrice) / basePrice
        }

        return {
          code,
          basePrice,
          currentPrice,
          dropPct,
          vwap: sd.current_vwap || null,
          state: sd.state || 'idle',
          stateLabel: STATE_LABELS[sd.state] || '待机',
          triggered: sd.has_position || false,
          watching: sd.state === 'watching'
        }
      })
    },
    getDropClass (pct) {
      if (pct === null) return ''
      if (pct <= -0.01) return 'drop-danger'
      if (pct <= -0.008) return 'drop-warning'
      if (pct < 0) return 'drop-mild'
      return 'drop-positive'
    }
  }
}
</script>

<style lang="less" scoped>
.monitor-panel {
  .symbol-card {
    border-radius: 8px;
    transition: all 0.3s;

    &.card-triggered {
      border-color: #ff4d4f;
      box-shadow: 0 2px 8px rgba(255, 77, 79, 0.2);
    }

    &.card-watching {
      border-color: #faad14;
      box-shadow: 0 2px 8px rgba(250, 173, 20, 0.15);
    }

    .symbol-title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .symbol-info {
    .info-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px dashed #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .label {
        color: #8c8c8c;
        font-size: 13px;
      }

      .value {
        font-weight: 500;
        font-family: 'Roboto Mono', monospace;
      }
    }
  }

  .text-profit { color: #52c41a; }
  .text-loss { color: #ff4d4f; }

  .drop-danger { color: #ff4d4f; font-weight: 700; }
  .drop-warning { color: #faad14; font-weight: 600; }
  .drop-mild { color: #ff7a45; }
  .drop-positive { color: #52c41a; }
}
</style>
