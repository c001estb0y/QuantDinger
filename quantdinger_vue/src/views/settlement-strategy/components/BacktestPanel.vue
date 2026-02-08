<template>
  <div class="backtest-panel">
    <!-- Backtest Parameters -->
    <a-card title="📊 回测参数" size="small" style="margin-bottom: 16px;">
      <a-form layout="inline">
        <a-form-item label="起止日期">
          <a-range-picker v-model="params.dateRange" style="width: 250px;" />
        </a-form-item>
        <a-form-item label="品种">
          <a-select v-model="params.symbols" mode="multiple" placeholder="选择品种" style="width: 250px;">
            <a-select-option value="IM0">IM (中证1000)</a-select-option>
            <a-select-option value="IC0">IC (中证500)</a-select-option>
            <a-select-option value="IF0">IF (沪深300)</a-select-option>
            <a-select-option value="IH0">IH (上证50)</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="首仓阈值(%)">
          <a-input-number v-model="params.threshold_1" :min="0.1" :max="5" :step="0.1" :precision="1" />
        </a-form-item>
        <a-form-item label="追加阈值(%)">
          <a-input-number v-model="params.threshold_2" :min="0.5" :max="10" :step="0.1" :precision="1" />
        </a-form-item>
        <a-form-item label="初始资金">
          <a-input-number v-model="params.initial_capital" :min="100000" :step="50000" style="width: 150px;" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="running" @click="handleRunBacktest">
            <a-icon type="experiment" /> 运行回测
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- Backtest Results -->
    <a-card v-if="hasResults" title="📈 回测结果" size="small">
      <a-alert
        v-if="backtestError"
        type="warning"
        :message="backtestError"
        show-icon
        style="margin-bottom: 16px;"
      />

      <!-- Performance Summary -->
      <a-row :gutter="16" style="margin-bottom: 16px;">
        <a-col :span="4">
          <a-statistic title="总收益率" :value="results.total_return" suffix="%" :precision="2" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="年化收益" :value="results.annual_return" suffix="%" :precision="2" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="夏普比率" :value="results.sharpe_ratio" :precision="2" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="最大回撤" :value="results.max_drawdown" suffix="%" :precision="2" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="胜率" :value="results.win_rate" suffix="%" :precision="1" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="交易次数" :value="results.total_trades" />
        </a-col>
      </a-row>

      <!-- Equity Curve Placeholder -->
      <div class="chart-placeholder">
        <a-icon type="line-chart" style="font-size: 48px; color: #d9d9d9;" />
        <p>累计收益曲线（待接入回测引擎）</p>
      </div>
    </a-card>

    <!-- Empty State -->
    <a-empty v-else description="设置参数并运行回测" style="padding: 48px;">
      <template slot="image">
        <a-icon type="experiment" style="font-size: 64px; color: #d9d9d9;" />
      </template>
    </a-empty>
  </div>
</template>

<script>
import { runBacktest } from '@/api/settlement-strategy'

export default {
  name: 'BacktestPanel',
  data () {
    return {
      params: {
        dateRange: [],
        symbols: ['IM0', 'IC0'],
        threshold_1: 1.0,
        threshold_2: 2.0,
        initial_capital: 500000
      },
      results: {},
      hasResults: false,
      running: false,
      backtestError: ''
    }
  },
  methods: {
    async handleRunBacktest () {
      if (!this.params.dateRange || this.params.dateRange.length !== 2) {
        this.$message.warning('请选择回测日期范围')
        return
      }
      if (this.params.symbols.length === 0) {
        this.$message.warning('请选择至少一个品种')
        return
      }

      this.running = true
      this.backtestError = ''

      try {
        const payload = {
          start_date: this.params.dateRange[0].format('YYYY-MM-DD'),
          end_date: this.params.dateRange[1].format('YYYY-MM-DD'),
          symbols: this.params.symbols,
          threshold_1: this.params.threshold_1 / 100,
          threshold_2: this.params.threshold_2 / 100,
          initial_capital: this.params.initial_capital
        }

        const res = await runBacktest(payload)
        if (res.success && res.data) {
          this.results = res.data
          this.hasResults = true
        } else {
          this.backtestError = res.message || '回测引擎正在开发中'
          this.hasResults = true
          this.results = {
            total_return: 0,
            annual_return: 0,
            sharpe_ratio: 0,
            max_drawdown: 0,
            win_rate: 0,
            total_trades: 0
          }
        }
      } catch (e) {
        this.backtestError = '回测引擎正在开发中 (Phase 7)'
        this.hasResults = true
        this.results = {
          total_return: 0,
          annual_return: 0,
          sharpe_ratio: 0,
          max_drawdown: 0,
          win_rate: 0,
          total_trades: 0
        }
      } finally {
        this.running = false
      }
    }
  }
}
</script>

<style lang="less" scoped>
.backtest-panel {
  .chart-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px;
    background: #fafafa;
    border-radius: 8px;
    border: 1px dashed #d9d9d9;

    p {
      margin-top: 16px;
      color: #8c8c8c;
    }
  }
}
</style>
