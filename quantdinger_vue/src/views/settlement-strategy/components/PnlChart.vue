<template>
  <div class="pnl-chart">
    <!-- Summary Cards -->
    <a-row :gutter="16" style="margin-bottom: 24px;">
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="总盈亏">
            <template slot="formatter">
              <span :class="summary.total_pnl >= 0 ? 'text-profit' : 'text-loss'">
                {{ summary.total_pnl >= 0 ? '+' : '' }}{{ summary.total_pnl.toFixed(2) }} 元
              </span>
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="胜率" :value="(summary.win_rate * 100).toFixed(1)" suffix="%" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="总交易次数" :value="summary.total_trades" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="手续费" :value="summary.total_fees" :precision="2" suffix="元" />
        </a-card>
      </a-col>
    </a-row>

    <!-- Detail Cards -->
    <a-row :gutter="16" style="margin-bottom: 24px;">
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="盈利次数" :value="summary.winning_trades" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="亏损次数" :value="summary.losing_trades" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="平均盈利">
            <template slot="formatter">
              <span class="text-profit">+{{ summary.avg_win.toFixed(2) }} 元</span>
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="true">
          <a-statistic title="平均亏损">
            <template slot="formatter">
              <span class="text-loss">{{ summary.avg_loss.toFixed(2) }} 元</span>
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- Risk Status -->
    <a-card title="🛡️ 风控状态" size="small" style="margin-bottom: 16px;">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic title="当前权益" :value="risk.current_equity" :precision="2" suffix="元" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="峰值权益" :value="risk.peak_equity" :precision="2" suffix="元" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="当前回撤" :value="(risk.current_drawdown * 100).toFixed(2)" suffix="%" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="日亏损余额" :value="risk.daily_loss_remaining" :precision="2" suffix="元" />
        </a-col>
      </a-row>
    </a-card>

    <!-- Risk Events -->
    <a-card title="⚠️ 风控事件" size="small">
      <a-table
        :columns="eventColumns"
        :data-source="riskEvents"
        :pagination="false"
        :locale="{ emptyText: '暂无风控事件' }"
        row-key="timestamp"
        size="small"
      />
    </a-card>
  </div>
</template>

<script>
import { getPnlSummary, getRiskEvents } from '@/api/settlement-strategy'

const eventColumns = [
  { title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: 180 },
  { title: '类型', dataIndex: 'event_type', key: 'event_type', width: 120,
    customRender: (text) => {
      const map = {
        'position_limit': '仓位限制',
        'daily_loss_limit': '日亏损限制',
        'drawdown_limit': '回撤限制',
        'force_close': '强制平仓'
      }
      return map[text] || text
    }
  },
  { title: '描述', dataIndex: 'message', key: 'message' },
  { title: '操作', dataIndex: 'action_taken', key: 'action_taken', width: 100,
    customRender: (text) => text || '--'
  }
]

export default {
  name: 'PnlChart',
  data () {
    return {
      summary: {
        total_pnl: 0,
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        avg_win: 0,
        avg_loss: 0,
        total_fees: 0
      },
      risk: {
        current_equity: 0,
        peak_equity: 0,
        current_drawdown: 0,
        daily_loss_remaining: 0
      },
      riskEvents: [],
      eventColumns,
      timer: null
    }
  },
  mounted () {
    this.fetchData()
    this.timer = setInterval(this.fetchData, 10000)
  },
  beforeDestroy () {
    clearInterval(this.timer)
  },
  methods: {
    async fetchData () {
      try {
        const [pnlRes, eventsRes] = await Promise.all([
          getPnlSummary(),
          getRiskEvents(20)
        ])

        if (pnlRes.success && pnlRes.data) {
          this.summary = pnlRes.data.pnl || this.summary
          this.risk = pnlRes.data.risk || this.risk
        }

        if (eventsRes.success && eventsRes.data) {
          this.riskEvents = eventsRes.data.events || []
        }
      } catch (e) {
        console.error('Failed to fetch PnL data:', e)
      }
    }
  }
}
</script>

<style lang="less" scoped>
.pnl-chart {
  .text-profit { color: #52c41a; font-weight: 500; }
  .text-loss { color: #ff4d4f; font-weight: 500; }
}
</style>
