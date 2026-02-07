<template>
  <div class="quote-panel">
    <a-spin :spinning="loading">
      <a-row :gutter="[16, 16]">
        <a-col
          v-for="symbol in selectedSymbols"
          :key="symbol"
          :xs="24"
          :sm="12"
          :lg="6"
        >
          <div class="quote-card" :class="{ 'has-data': quotes[symbol] }">
            <!-- Header -->
            <div class="quote-header">
              <span class="symbol">{{ symbol }}</span>
              <span class="name">{{ getContractName(symbol) }}</span>
            </div>

            <!-- Content -->
            <div v-if="quotes[symbol]" class="quote-content">
              <!-- Last Price -->
              <div class="price-row">
                <span class="price-label">最新价</span>
                <span
                  class="price-value"
                  :class="getPriceClass(symbol)"
                >
                  {{ formatPrice(quotes[symbol].last) }}
                </span>
              </div>

              <!-- Change -->
              <div class="change-row">
                <span
                  class="change-value"
                  :class="getChangeClass(symbol)"
                >
                  {{ formatChange(symbol) }}
                </span>
              </div>

              <!-- Details -->
              <div class="detail-row">
                <div class="detail-item">
                  <span class="detail-label">买价</span>
                  <span class="detail-value">{{ formatPrice(quotes[symbol].bid) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">卖价</span>
                  <span class="detail-value">{{ formatPrice(quotes[symbol].ask) }}</span>
                </div>
              </div>

              <div class="detail-row">
                <div class="detail-item">
                  <span class="detail-label">成交量</span>
                  <span class="detail-value">{{ formatVolume(quotes[symbol].volume) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">合约价值</span>
                  <span class="detail-value">{{ formatMoney(quotes[symbol].contract_value) }}</span>
                </div>
              </div>

              <!-- Margin -->
              <div class="margin-row">
                <span class="margin-label">保证金</span>
                <span class="margin-value">{{ formatMoney(quotes[symbol].margin_required) }}</span>
              </div>
            </div>

            <!-- No Data -->
            <div v-else class="no-data">
              <a-empty :image="null" description="暂无数据" />
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- Empty State -->
      <a-empty
        v-if="selectedSymbols.length === 0"
        description="请选择要监控的合约"
      />
    </a-spin>
  </div>
</template>

<script>
export default {
  name: 'QuotePanel',
  props: {
    quotes: {
      type: Object,
      default: () => ({})
    },
    selectedSymbols: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  setup (props) {
    const contractNames = {
      'IC0': '中证500',
      'IM0': '中证1000',
      'IF0': '沪深300',
      'IH0': '上证50'
    }

    const getContractName = (symbol) => {
      return contractNames[symbol] || symbol
    }

    const formatPrice = (price) => {
      if (!price) return '-'
      return Number(price).toFixed(2)
    }

    const formatVolume = (volume) => {
      if (!volume) return '-'
      if (volume >= 10000) {
        return (volume / 10000).toFixed(2) + '万'
      }
      return volume.toString()
    }

    const formatMoney = (value) => {
      if (!value) return '-'
      if (value >= 10000) {
        return '¥' + (value / 10000).toFixed(2) + '万'
      }
      return '¥' + value.toFixed(2)
    }

    const formatChange = (symbol) => {
      const quote = props.quotes[symbol]
      if (!quote || !quote.last) return '-'

      // Calculate change from base price (previous close or settlement)
      const basePrice = quote.contract_info?.prev_settlement || quote.last * 0.99 // Fallback
      const change = quote.last - basePrice
      const changePercent = ((change / basePrice) * 100).toFixed(2)

      const sign = change >= 0 ? '+' : ''
      return `${sign}${change.toFixed(2)} (${sign}${changePercent}%)`
    }

    const getPriceClass = (symbol) => {
      const quote = props.quotes[symbol]
      if (!quote || !quote.last) return ''

      const basePrice = quote.contract_info?.prev_settlement || quote.last * 0.99
      if (quote.last > basePrice) return 'price-up'
      if (quote.last < basePrice) return 'price-down'
      return ''
    }

    const getChangeClass = (symbol) => {
      return getPriceClass(symbol)
    }

    return {
      getContractName,
      formatPrice,
      formatVolume,
      formatMoney,
      formatChange,
      getPriceClass,
      getChangeClass
    }
  }
}
</script>

<style lang="less" scoped>
.quote-panel {
  .quote-card {
    background: #fafafa;
    border: 1px solid #f0f0f0;
    border-radius: 8px;
    padding: 16px;
    transition: all 0.3s;

    &.has-data:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .quote-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #f0f0f0;

      .symbol {
        font-size: 16px;
        font-weight: 600;
        color: #262626;
      }

      .name {
        font-size: 12px;
        color: #8c8c8c;
      }
    }

    .quote-content {
      .price-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;

        .price-label {
          font-size: 12px;
          color: #8c8c8c;
        }

        .price-value {
          font-size: 24px;
          font-weight: 600;
          color: #262626;

          &.price-up {
            color: #52c41a; // Green for up (China market convention: red up, green down - but we use international)
          }

          &.price-down {
            color: #ff4d4f; // Red for down
          }
        }
      }

      .change-row {
        text-align: right;
        margin-bottom: 12px;

        .change-value {
          font-size: 14px;
          color: #262626;

          &.price-up {
            color: #52c41a;
          }

          &.price-down {
            color: #ff4d4f;
          }
        }
      }

      .detail-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;

        .detail-item {
          display: flex;
          flex-direction: column;

          .detail-label {
            font-size: 11px;
            color: #bfbfbf;
          }

          .detail-value {
            font-size: 13px;
            color: #595959;
          }
        }
      }

      .margin-row {
        margin-top: 12px;
        padding-top: 8px;
        border-top: 1px dashed #f0f0f0;
        display: flex;
        justify-content: space-between;

        .margin-label {
          font-size: 12px;
          color: #8c8c8c;
        }

        .margin-value {
          font-size: 14px;
          font-weight: 500;
          color: #1890ff;
        }
      }
    }

    .no-data {
      padding: 20px 0;
    }
  }
}
</style>
