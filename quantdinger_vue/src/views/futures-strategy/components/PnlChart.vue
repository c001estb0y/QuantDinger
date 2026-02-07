<template>
  <div class="pnl-chart">
    <a-spin :spinning="loading">
      <!-- Summary Cards -->
      <a-row :gutter="[8, 8]" class="summary-cards">
        <a-col :span="8">
          <div class="summary-card">
            <div class="summary-label">本期盈亏</div>
            <div class="summary-value" :class="getPnlClass(summary.net_pnl)">
              {{ formatMoney(summary.net_pnl) }}
            </div>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="summary-card">
            <div class="summary-label">胜率</div>
            <div class="summary-value">
              {{ formatPercent(summary.win_rate) }}
            </div>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="summary-card">
            <div class="summary-label">交易次数</div>
            <div class="summary-value">
              {{ summary.trade_count || 0 }}
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- Period Selector -->
      <div class="period-selector">
<a-radio-group
          v-model="selectedPeriod"
          size="small"
          @change="handlePeriodChange"
        >
          <a-radio-button value="day">日</a-radio-button>
          <a-radio-button value="week">周</a-radio-button>
          <a-radio-button value="month">月</a-radio-button>
          <a-radio-button value="year">年</a-radio-button>
        </a-radio-group>
      </div>

      <!-- Chart -->
      <div ref="chartRef" class="chart-container"></div>

      <!-- Detail Stats -->
      <div class="detail-stats">
        <div class="stat-row">
          <span class="stat-label">总盈亏</span>
          <span class="stat-value" :class="getPnlClass(summary.total_pnl)">
            {{ formatMoney(summary.total_pnl) }}
          </span>
        </div>
        <div class="stat-row">
          <span class="stat-label">总手续费</span>
          <span class="stat-value negative">{{ formatMoney(summary.total_fee) }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">盈利次数</span>
          <span class="stat-value positive">{{ summary.win_count || 0 }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">亏损次数</span>
          <span class="stat-value negative">{{ summary.loss_count || 0 }}</span>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// Register ECharts components
echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  LineChart,
  CanvasRenderer
])

export default {
  name: 'PnlChart',
  props: {
    summary: {
      type: Object,
      default: () => ({
        total_pnl: 0,
        total_fee: 0,
        net_pnl: 0,
        trade_count: 0,
        win_count: 0,
        loss_count: 0,
        win_rate: 0
      })
    },
    history: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    period: {
      type: String,
      default: 'month'
    }
  },
  emits: ['period-change'],
  setup (props, { emit }) {
    const chartRef = ref(null)
    const selectedPeriod = ref(props.period)
    let chartInstance = null

    // Watch for period prop changes
    watch(() => props.period, (newPeriod) => {
      selectedPeriod.value = newPeriod
    })

    // Watch for history data changes
    watch(() => props.history, () => {
      updateChart()
    }, { deep: true })

    const initChart = () => {
      if (!chartRef.value) return

      chartInstance = echarts.init(chartRef.value)
      updateChart()

      // Handle resize
      window.addEventListener('resize', handleResize)
    }

    const updateChart = () => {
      if (!chartInstance) return

      const dates = props.history.map(item => item.date)
      const dailyPnl = props.history.map(item => item.daily_pnl || 0)
      const cumulativePnl = props.history.map(item => item.cumulative_pnl || 0)

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const date = params[0].axisValue
            let html = `<div style="font-weight:600">${date}</div>`
            params.forEach(param => {
              const value = param.value >= 0 ? '+' + param.value.toFixed(2) : param.value.toFixed(2)
              html += `<div>${param.marker}${param.seriesName}: ¥${value}</div>`
            })
            return html
          }
        },
        legend: {
          data: ['日盈亏', '累计盈亏'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: {
            fontSize: 10,
            rotate: 45
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            fontSize: 10,
            formatter: (value) => {
              if (Math.abs(value) >= 10000) {
                return (value / 10000).toFixed(1) + '万'
              }
              return value
            }
          },
          splitLine: {
            lineStyle: {
              type: 'dashed'
            }
          }
        },
        series: [
          {
            name: '日盈亏',
            type: 'line',
            data: dailyPnl,
            smooth: true,
            lineStyle: {
              width: 2
            },
            itemStyle: {
              color: '#1890ff'
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
                { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
              ])
            }
          },
          {
            name: '累计盈亏',
            type: 'line',
            data: cumulativePnl,
            smooth: true,
            lineStyle: {
              width: 2
            },
            itemStyle: {
              color: '#52c41a'
            }
          }
        ]
      }

      chartInstance.setOption(option)
    }

    const handleResize = () => {
      if (chartInstance) {
        chartInstance.resize()
      }
    }

    const handlePeriodChange = (e) => {
      emit('period-change', e.target.value)
    }

    const formatMoney = (value) => {
      if (!value) return '¥0.00'
      const sign = value >= 0 ? '+' : ''
      if (Math.abs(value) >= 10000) {
        return sign + '¥' + (value / 10000).toFixed(2) + '万'
      }
      return sign + '¥' + Number(value).toFixed(2)
    }

    const formatPercent = (value) => {
      if (!value) return '0%'
      return value.toFixed(1) + '%'
    }

    const getPnlClass = (value) => {
      if (value > 0) return 'positive'
      if (value < 0) return 'negative'
      return ''
    }

    onMounted(() => {
      nextTick(() => {
        initChart()
      })
    })

    onUnmounted(() => {
      window.removeEventListener('resize', handleResize)
      if (chartInstance) {
        chartInstance.dispose()
        chartInstance = null
      }
    })

    return {
      chartRef,
      selectedPeriod,
      handlePeriodChange,
      formatMoney,
      formatPercent,
      getPnlClass
    }
  }
}
</script>

<style lang="less" scoped>
.pnl-chart {
  .summary-cards {
    margin-bottom: 16px;

    .summary-card {
      background: #fafafa;
      border-radius: 4px;
      padding: 12px 8px;
      text-align: center;

      .summary-label {
        font-size: 12px;
        color: #8c8c8c;
        margin-bottom: 4px;
      }

      .summary-value {
        font-size: 16px;
        font-weight: 600;
        color: #262626;

        &.positive {
          color: #52c41a;
        }

        &.negative {
          color: #ff4d4f;
        }
      }
    }
  }

  .period-selector {
    text-align: center;
    margin-bottom: 16px;
  }

  .chart-container {
    width: 100%;
    height: 200px;
  }

  .detail-stats {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;

    .stat-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;

      .stat-label {
        font-size: 12px;
        color: #8c8c8c;
      }

      .stat-value {
        font-size: 13px;
        color: #262626;

        &.positive {
          color: #52c41a;
        }

        &.negative {
          color: #ff4d4f;
        }
      }
    }
  }
}
</style>
