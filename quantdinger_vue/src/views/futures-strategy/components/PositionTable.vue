<template>
  <div class="position-table">
    <a-table
      :columns="columns"
      :data-source="enrichedPositions"
      :loading="loading"
      :pagination="false"
      size="small"
      row-key="id"
    >
      <!-- Direction -->
      <template #direction="{ record }">
        <a-tag :color="record.direction === 'long' ? 'green' : 'red'">
          {{ record.direction === 'long' ? '多' : '空' }}
        </a-tag>
      </template>

      <!-- Entry Price -->
      <template #entry_price="{ record }">
        {{ formatPrice(record.entry_price) }}
      </template>

      <!-- Current Price -->
      <template #current_price="{ record }">
        <span :class="getPriceClass(record)">
          {{ formatPrice(record.current_price) }}
        </span>
      </template>

      <!-- PnL -->
      <template #pnl="{ record }">
        <span :class="getPnlClass(record.unrealized_pnl)">
          {{ formatPnl(record.unrealized_pnl) }}
        </span>
      </template>

      <!-- PnL Percent -->
      <template #pnl_pct="{ record }">
        <span :class="getPnlClass(record.pnl_percent)">
          {{ formatPercent(record.pnl_percent) }}
        </span>
      </template>

      <!-- Entry Time -->
      <template #entry_time="{ record }">
        {{ formatTime(record.entry_time) }}
      </template>
    </a-table>

    <!-- Empty state -->
    <a-empty
      v-if="!loading && positions.length === 0"
      description="暂无持仓"
    />
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'PositionTable',
  props: {
    positions: {
      type: Array,
      default: () => []
    },
    quotes: {
      type: Object,
      default: () => ({})
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  setup (props) {
    const columns = [
      {
        title: '合约',
        dataIndex: 'symbol',
        key: 'symbol',
        width: 80
      },
      {
        title: '方向',
        dataIndex: 'direction',
        key: 'direction',
        width: 60,
        slots: { customRender: 'direction' }
      },
      {
        title: '数量',
        dataIndex: 'quantity',
        key: 'quantity',
        width: 60
      },
      {
        title: '开仓价',
        dataIndex: 'entry_price',
        key: 'entry_price',
        width: 100,
        slots: { customRender: 'entry_price' }
      },
      {
        title: '现价',
        dataIndex: 'current_price',
        key: 'current_price',
        width: 100,
        slots: { customRender: 'current_price' }
      },
      {
        title: '盈亏',
        dataIndex: 'unrealized_pnl',
        key: 'pnl',
        width: 100,
        slots: { customRender: 'pnl' }
      },
      {
        title: '盈亏%',
        dataIndex: 'pnl_percent',
        key: 'pnl_pct',
        width: 80,
        slots: { customRender: 'pnl_pct' }
      },
      {
        title: '开仓时间',
        dataIndex: 'entry_time',
        key: 'entry_time',
        width: 140,
        slots: { customRender: 'entry_time' }
      }
    ]

    // Enrich positions with current price and calculated PnL
    const enrichedPositions = computed(() => {
      return props.positions.map(pos => {
        const quote = props.quotes[pos.symbol]
        const currentPrice = quote?.last || pos.entry_price

        // Calculate unrealized PnL
        const priceDiff = pos.direction === 'long'
          ? currentPrice - pos.entry_price
          : pos.entry_price - currentPrice

        // Get multiplier from quote or use default
        const multiplier = quote?.contract_info?.multiplier ||
          (pos.symbol.startsWith('IF') || pos.symbol.startsWith('IH') ? 300 : 200)

        const unrealizedPnl = priceDiff * multiplier * pos.quantity
        const pnlPercent = (priceDiff / pos.entry_price) * 100

        return {
          ...pos,
          current_price: currentPrice,
          unrealized_pnl: unrealizedPnl,
          pnl_percent: pnlPercent
        }
      })
    })

    const formatPrice = (price) => {
      if (!price) return '-'
      return Number(price).toFixed(2)
    }

    const formatPnl = (pnl) => {
      if (pnl === undefined || pnl === null) return '-'
      const sign = pnl >= 0 ? '+' : ''
      return sign + '¥' + Number(pnl).toFixed(2)
    }

    const formatPercent = (pct) => {
      if (pct === undefined || pct === null) return '-'
      const sign = pct >= 0 ? '+' : ''
      return sign + Number(pct).toFixed(2) + '%'
    }

    const formatTime = (time) => {
      if (!time) return '-'
      const date = new Date(time)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const getPriceClass = (record) => {
      if (record.current_price > record.entry_price) return 'price-up'
      if (record.current_price < record.entry_price) return 'price-down'
      return ''
    }

    const getPnlClass = (value) => {
      if (value > 0) return 'pnl-positive'
      if (value < 0) return 'pnl-negative'
      return ''
    }

    return {
      columns,
      enrichedPositions,
      formatPrice,
      formatPnl,
      formatPercent,
      formatTime,
      getPriceClass,
      getPnlClass
    }
  }
}
</script>

<style lang="less" scoped>
.position-table {
  .price-up {
    color: #52c41a;
  }

  .price-down {
    color: #ff4d4f;
  }

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
