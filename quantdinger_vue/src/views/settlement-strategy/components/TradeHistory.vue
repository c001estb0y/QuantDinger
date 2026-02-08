<template>
  <div class="trade-history">
    <!-- Filters -->
    <a-row :gutter="16" style="margin-bottom: 16px;">
      <a-col :span="6">
        <a-select v-model="filters.symbol" placeholder="全部品种" allow-clear style="width: 100%;">
          <a-select-option value="IM0">IM (中证1000)</a-select-option>
          <a-select-option value="IC0">IC (中证500)</a-select-option>
          <a-select-option value="IF0">IF (沪深300)</a-select-option>
          <a-select-option value="IH0">IH (上证50)</a-select-option>
        </a-select>
      </a-col>
      <a-col :span="8">
        <a-range-picker v-model="filters.dateRange" style="width: 100%;" />
      </a-col>
      <a-col :span="4">
        <a-button type="primary" @click="fetchTrades">
          <a-icon type="search" /> 查询
        </a-button>
      </a-col>
    </a-row>

    <!-- Trade Table -->
    <a-table
      :columns="columns"
      :data-source="trades"
      :loading="loading"
      :pagination="pagination"
      :locale="{ emptyText: '暂无交易记录' }"
      row-key="id"
      size="middle"
      @change="handleTableChange"
    >
      <template slot="pnl" slot-scope="text">
        <span :class="text >= 0 ? 'text-profit' : 'text-loss'">
          {{ text >= 0 ? '+' : '' }}{{ text.toFixed(2) }}
        </span>
      </template>
      <template slot="direction" slot-scope="text">
        <a-tag :color="text === 'long' ? 'green' : 'red'">
          {{ text === 'long' ? '多' : '空' }}
        </a-tag>
      </template>
    </a-table>
  </div>
</template>

<script>
import { getTrades } from '@/api/settlement-strategy'

const columns = [
  { title: '平仓时间', dataIndex: 'exit_time', key: 'exit_time', width: 180 },
  { title: '合约', dataIndex: 'symbol', key: 'symbol', width: 80 },
  { title: '方向', dataIndex: 'direction', key: 'direction', width: 60, scopedSlots: { customRender: 'direction' } },
  { title: '档位', dataIndex: 'level', key: 'level', width: 60,
    customRender: (text) => `L${text}`
  },
  { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 60 },
  { title: '开仓价', dataIndex: 'entry_price', key: 'entry_price', width: 100 },
  { title: '平仓价', dataIndex: 'exit_price', key: 'exit_price', width: 100 },
  { title: '盈亏', dataIndex: 'net_pnl', key: 'net_pnl', width: 100, scopedSlots: { customRender: 'pnl' } },
  { title: '手续费', dataIndex: 'fee', key: 'fee', width: 80,
    customRender: (text) => text ? text.toFixed(2) : '--'
  },
  { title: '持仓时长', dataIndex: 'holding_hours', key: 'holding_hours', width: 100,
    customRender: (text) => text ? text.toFixed(1) + 'h' : '--'
  }
]

export default {
  name: 'TradeHistory',
  data () {
    return {
      columns,
      trades: [],
      loading: false,
      filters: {
        symbol: undefined,
        dateRange: []
      },
      pagination: {
        current: 1,
        pageSize: 20,
        total: 0,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`
      }
    }
  },
  mounted () {
    this.fetchTrades()
  },
  methods: {
    async fetchTrades () {
      this.loading = true
      try {
        const params = {
          page: this.pagination.current,
          page_size: this.pagination.pageSize
        }

        if (this.filters.symbol) {
          params.symbol = this.filters.symbol
        }

        if (this.filters.dateRange && this.filters.dateRange.length === 2) {
          params.start_date = this.filters.dateRange[0].format('YYYY-MM-DD')
          params.end_date = this.filters.dateRange[1].format('YYYY-MM-DD')
        }

        const res = await getTrades(params)
        if (res.success && res.data) {
          this.trades = res.data.trades || []
          this.pagination.total = res.data.total || 0
        }
      } catch (e) {
        console.error('Failed to fetch trades:', e)
      } finally {
        this.loading = false
      }
    },
    handleTableChange (pagination) {
      this.pagination.current = pagination.current
      this.pagination.pageSize = pagination.pageSize
      this.fetchTrades()
    }
  }
}
</script>

<style lang="less" scoped>
.trade-history {
  .text-profit { color: #52c41a; font-weight: 500; }
  .text-loss { color: #ff4d4f; font-weight: 500; }
}
</style>
