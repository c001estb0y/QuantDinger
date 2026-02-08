<template>
  <div class="position-table">
    <!-- Summary Cards -->
    <a-row :gutter="16" style="margin-bottom: 16px;">
      <a-col :span="6">
        <a-statistic title="持仓数量" :value="positions.length" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="总手数" :value="totalQuantity" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="占用保证金" :value="totalMargin" :precision="0" suffix="元" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="浮动盈亏">
          <span :class="totalUnrealizedPnl >= 0 ? 'text-profit' : 'text-loss'">
            {{ totalUnrealizedPnl >= 0 ? '+' : '' }}{{ totalUnrealizedPnl.toFixed(2) }} 元
          </span>
        </a-statistic>
      </a-col>
    </a-row>

    <!-- Position Table -->
    <a-table
      :columns="columns"
      :data-source="positions"
      :pagination="false"
      :loading="loading"
      :locale="{ emptyText: '暂无持仓' }"
      row-key="id"
      size="middle"
    >
      <template slot="direction" slot-scope="text">
        <a-tag :color="text === 'long' ? 'green' : 'red'">
          {{ text === 'long' ? '多' : '空' }}
        </a-tag>
      </template>
      <template slot="level" slot-scope="text">
        <a-tag :color="text === 1 ? 'blue' : 'orange'">
          L{{ text }}
        </a-tag>
      </template>
      <template slot="pnl" slot-scope="text, record">
        <span :class="record.unrealizedPnl >= 0 ? 'text-profit' : 'text-loss'">
          {{ record.unrealizedPnl >= 0 ? '+' : '' }}{{ record.unrealizedPnl.toFixed(2) }}
        </span>
      </template>
    </a-table>
  </div>
</template>

<script>
import { getPositions } from '@/api/settlement-strategy'

const columns = [
  { title: '合约', dataIndex: 'symbol', key: 'symbol', width: 80 },
  { title: '方向', dataIndex: 'direction', key: 'direction', width: 60, scopedSlots: { customRender: 'direction' } },
  { title: '档位', dataIndex: 'level', key: 'level', width: 60, scopedSlots: { customRender: 'level' } },
  { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 60 },
  { title: '开仓价', dataIndex: 'entry_price', key: 'entry_price', width: 100 },
  { title: '基准价', dataIndex: 'base_price', key: 'base_price', width: 100 },
  { title: '跌幅', dataIndex: 'drop_pct', key: 'drop_pct', width: 80,
    customRender: (text) => text ? (text * 100).toFixed(2) + '%' : '--'
  },
  { title: '保证金', dataIndex: 'margin', key: 'margin', width: 100,
    customRender: (text) => text ? text.toFixed(0) + '元' : '--'
  },
  { title: '浮盈', key: 'pnl', width: 100, scopedSlots: { customRender: 'pnl' } },
  { title: '开仓时间', dataIndex: 'entry_time', key: 'entry_time', width: 180 }
]

export default {
  name: 'PositionTable',
  props: {
    isRunning: { type: Boolean, default: false }
  },
  data () {
    return {
      columns,
      positions: [],
      totalMargin: 0,
      loading: false,
      timer: null
    }
  },
  computed: {
    totalQuantity () {
      return this.positions.reduce((sum, p) => sum + (p.quantity || 0), 0)
    },
    totalUnrealizedPnl () {
      return this.positions.reduce((sum, p) => sum + (p.unrealizedPnl || 0), 0)
    }
  },
  mounted () {
    this.fetchPositions()
    this.timer = setInterval(this.fetchPositions, 5000)
  },
  beforeDestroy () {
    clearInterval(this.timer)
  },
  methods: {
    async fetchPositions () {
      try {
        this.loading = true
        const res = await getPositions()
        if (res.success && res.data) {
          this.positions = (res.data.positions || []).map(p => ({
            ...p,
            unrealizedPnl: p.unrealized_pnl || 0
          }))
          this.totalMargin = res.data.total_margin || 0
        }
      } catch (e) {
        console.error('Failed to fetch positions:', e)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="less" scoped>
.position-table {
  .text-profit { color: #52c41a; font-weight: 500; }
  .text-loss { color: #ff4d4f; font-weight: 500; }
}
</style>
