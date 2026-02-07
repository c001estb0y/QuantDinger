<template>
  <div class="trade-history">
    <a-table
      :columns="columns"
      :data-source="trades"
      :loading="loading"
      :pagination="paginationConfig"
      size="small"
      row-key="id"
      @change="handleTableChange"
    >
      <!-- Trade Type -->
      <template #trade_type="{ record }">
        <a-tag :color="getTradeTypeColor(record.trade_type)">
          {{ getTradeTypeText(record.trade_type) }}
        </a-tag>
      </template>

      <!-- Price -->
      <template #price="{ record }">
        {{ formatPrice(record.price) }}
      </template>

      <!-- Fee -->
      <template #fee="{ record }">
        {{ formatMoney(record.fee) }}
      </template>

      <!-- PnL -->
      <template #pnl="{ record }">
        <span :class="getPnlClass(record.pnl)">
          {{ formatPnl(record.pnl) }}
        </span>
      </template>

      <!-- Trade Time -->
      <template #trade_time="{ record }">
        {{ formatTime(record.trade_time) }}
      </template>
    </a-table>

    <!-- Empty state -->
    <a-empty
      v-if="!loading && trades.length === 0"
      description="暂无交易记录"
    />
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'TradeHistory',
  props: {
    trades: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    pagination: {
      type: Object,
      default: () => ({
        current: 1,
        pageSize: 10,
        total: 0
      })
    }
  },
  emits: ['page-change'],
  setup (props, { emit }) {
    const columns = [
      {
        title: '时间',
        dataIndex: 'trade_time',
        key: 'trade_time',
        width: 140,
        slots: { customRender: 'trade_time' }
      },
      {
        title: '合约',
        dataIndex: 'symbol',
        key: 'symbol',
        width: 70
      },
      {
        title: '类型',
        dataIndex: 'trade_type',
        key: 'trade_type',
        width: 80,
        slots: { customRender: 'trade_type' }
      },
      {
        title: '价格',
        dataIndex: 'price',
        key: 'price',
        width: 90,
        slots: { customRender: 'price' }
      },
      {
        title: '数量',
        dataIndex: 'quantity',
        key: 'quantity',
        width: 60
      },
      {
        title: '盈亏',
        dataIndex: 'pnl',
        key: 'pnl',
        width: 100,
        slots: { customRender: 'pnl' }
      },
      {
        title: '手续费',
        dataIndex: 'fee',
        key: 'fee',
        width: 80,
        slots: { customRender: 'fee' }
      }
    ]

    const paginationConfig = computed(() => ({
      current: props.pagination.current,
      pageSize: props.pagination.pageSize,
      total: props.pagination.total,
      showSizeChanger: false,
      showQuickJumper: true,
      size: 'small'
    }))

    const getTradeTypeColor = (type) => {
      const colors = {
        'open_long': 'green',
        'open_short': 'red',
        'close_long': 'orange',
        'close_short': 'blue',
        'buy': 'green',
        'sell': 'red'
      }
      return colors[type] || 'default'
    }

    const getTradeTypeText = (type) => {
      const texts = {
        'open_long': '开多',
        'open_short': '开空',
        'close_long': '平多',
        'close_short': '平空',
        'buy': '买入',
        'sell': '卖出'
      }
      return texts[type] || type
    }

    const formatPrice = (price) => {
      if (!price) return '-'
      return Number(price).toFixed(2)
    }

    const formatMoney = (value) => {
      if (!value) return '-'
      return '¥' + Number(value).toFixed(2)
    }

    const formatPnl = (pnl) => {
      if (pnl === undefined || pnl === null || pnl === 0) return '-'
      const sign = pnl >= 0 ? '+' : ''
      return sign + '¥' + Number(pnl).toFixed(2)
    }

    const formatTime = (time) => {
      if (!time) return '-'
      const date = new Date(time)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    const getPnlClass = (pnl) => {
      if (pnl > 0) return 'pnl-positive'
      if (pnl < 0) return 'pnl-negative'
      return ''
    }

    const handleTableChange = (pag) => {
      emit('page-change', pag.current)
    }

    return {
      columns,
      paginationConfig,
      getTradeTypeColor,
      getTradeTypeText,
      formatPrice,
      formatMoney,
      formatPnl,
      formatTime,
      getPnlClass,
      handleTableChange
    }
  }
}
</script>

<style lang="less" scoped>
.trade-history {
  .pnl-positive {
    color: #52c41a;
    font-weight: 500;
  }

  .pnl-negative {
    color: #ff4d4f;
    font-weight: 500;
  }
}
</style>
