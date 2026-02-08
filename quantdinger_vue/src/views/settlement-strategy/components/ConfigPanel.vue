<template>
  <div class="config-panel">
    <a-form :form="form" layout="vertical">
      <!-- Trading Symbols -->
      <a-card title="📊 交易品种" size="small" style="margin-bottom: 16px;">
        <a-form-item label="选择品种">
          <a-checkbox-group v-model="config.symbols">
            <a-checkbox value="IM0">IM (中证1000)</a-checkbox>
            <a-checkbox value="IC0">IC (中证500)</a-checkbox>
            <a-checkbox value="IF0">IF (沪深300)</a-checkbox>
            <a-checkbox value="IH0">IH (上证50)</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-card>

      <!-- Entry Conditions -->
      <a-card title="🎯 入场条件" size="small" style="margin-bottom: 16px;">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="首仓阈值 (%)">
              <a-input-number
                v-model="config.threshold_1"
                :min="0.1"
                :max="5"
                :step="0.1"
                :precision="1"
                style="width: 100%;"
              />
              <div class="hint">价格下跌超过此比例时首次买入</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="追加阈值 (%)">
              <a-input-number
                v-model="config.threshold_2"
                :min="0.5"
                :max="10"
                :step="0.1"
                :precision="1"
                style="width: 100%;"
              />
              <div class="hint">价格下跌超过此比例时追加买入</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="预警阈值 (%)">
              <a-input-number
                v-model="config.alert_threshold"
                :min="0.1"
                :max="5"
                :step="0.1"
                :precision="1"
                style="width: 100%;"
              />
              <div class="hint">接近入场时发送预警通知</div>
            </a-form-item>
          </a-col>
        </a-row>
      </a-card>

      <!-- Position Management -->
      <a-card title="📐 仓位管理" size="small" style="margin-bottom: 16px;">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="首仓手数">
              <a-input-number
                v-model="config.position_size_1"
                :min="1"
                :max="10"
                style="width: 100%;"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="追加手数">
              <a-input-number
                v-model="config.position_size_2"
                :min="1"
                :max="10"
                style="width: 100%;"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="单品种最大持仓">
              <a-input-number
                v-model="config.max_position_per_symbol"
                :min="1"
                :max="10"
                style="width: 100%;"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-card>

      <!-- Risk Management -->
      <a-card title="🛡️ 风控设置" size="small" style="margin-bottom: 16px;">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="单日最大亏损 (元)">
              <a-input-number
                v-model="config.max_daily_loss"
                :min="1000"
                :max="100000"
                :step="1000"
                style="width: 100%;"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="最大回撤 (%)">
              <a-input-number
                v-model="config.max_drawdown_pct"
                :min="1"
                :max="20"
                :step="0.5"
                :precision="1"
                style="width: 100%;"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="触发后强制平仓">
              <a-switch v-model="config.force_close_on_limit" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-card>

      <!-- Notification Settings -->
      <a-card title="🔔 通知设置" size="small" style="margin-bottom: 16px;">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="买入信号通知">
              <a-switch v-model="config.notify_on_entry" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="卖出信号通知">
              <a-switch v-model="config.notify_on_exit" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="价格预警通知">
              <a-switch v-model="config.notify_on_alert" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-card>

      <!-- Actions -->
      <div class="form-actions">
        <a-space>
          <a-button type="primary" :loading="saving" @click="handleSave">
            <a-icon type="save" /> 保存配置
          </a-button>
          <a-button @click="handleReset">
            <a-icon type="undo" /> 恢复默认
          </a-button>
        </a-space>
        <span v-if="isRunning" class="running-hint">
          <a-icon type="info-circle" /> 策略运行中，配置修改将实时生效
        </span>
      </div>
    </a-form>
  </div>
</template>

<script>
import { getStrategyConfig, updateStrategyConfig } from '@/api/settlement-strategy'

const DEFAULT_CONFIG = {
  symbols: ['IM0', 'IC0'],
  threshold_1: 1.0,
  threshold_2: 2.0,
  alert_threshold: 0.8,
  position_size_1: 1,
  position_size_2: 1,
  max_position_per_symbol: 2,
  max_daily_loss: 10000,
  max_drawdown_pct: 5.0,
  force_close_on_limit: true,
  notify_on_entry: true,
  notify_on_exit: true,
  notify_on_alert: true
}

export default {
  name: 'ConfigPanel',
  props: {
    isRunning: { type: Boolean, default: false }
  },
  data () {
    return {
      form: this.$form.createForm(this),
      config: { ...DEFAULT_CONFIG },
      saving: false
    }
  },
  mounted () {
    this.loadConfig()
  },
  methods: {
    async loadConfig () {
      try {
        const res = await getStrategyConfig()
        if (res.success && res.data) {
          const s = res.data.strategy || {}
          const r = res.data.risk || {}
          this.config = {
            symbols: s.symbols || DEFAULT_CONFIG.symbols,
            threshold_1: (s.threshold_1 || 0.01) * 100,
            threshold_2: (s.threshold_2 || 0.02) * 100,
            alert_threshold: (s.alert_threshold || 0.008) * 100,
            position_size_1: s.position_size_1 || 1,
            position_size_2: s.position_size_2 || 1,
            max_position_per_symbol: s.max_position_per_symbol || 2,
            max_daily_loss: r.max_daily_loss || 10000,
            max_drawdown_pct: (r.max_drawdown || 0.05) * 100,
            force_close_on_limit: r.force_close_on_limit !== false,
            notify_on_entry: s.notify_on_entry !== false,
            notify_on_exit: s.notify_on_exit !== false,
            notify_on_alert: s.notify_on_alert !== false
          }
        }
      } catch (e) {
        console.error('Failed to load config:', e)
      }
    },
    async handleSave () {
      if (this.config.symbols.length === 0) {
        this.$message.warning('请至少选择一个交易品种')
        return
      }

      this.saving = true
      try {
        const payload = {
          symbols: this.config.symbols,
          threshold_1: this.config.threshold_1 / 100,
          threshold_2: this.config.threshold_2 / 100,
          alert_threshold: this.config.alert_threshold / 100,
          position_size_1: this.config.position_size_1,
          position_size_2: this.config.position_size_2,
          max_position_per_symbol: this.config.max_position_per_symbol,
          max_daily_loss: this.config.max_daily_loss,
          max_drawdown: this.config.max_drawdown_pct / 100,
          force_close_on_limit: this.config.force_close_on_limit,
          notify_on_entry: this.config.notify_on_entry,
          notify_on_exit: this.config.notify_on_exit,
          notify_on_alert: this.config.notify_on_alert
        }

        const res = await updateStrategyConfig(payload)
        if (res.success) {
          this.$message.success('配置保存成功')
          this.$emit('config-saved')
        } else {
          this.$message.error(res.message || '保存失败')
        }
      } catch (e) {
        this.$message.error('保存配置失败: ' + (e.message || '未知错误'))
      } finally {
        this.saving = false
      }
    },
    handleReset () {
      this.config = { ...DEFAULT_CONFIG }
      this.$message.info('已恢复默认配置（未保存）')
    }
  }
}
</script>

<style lang="less" scoped>
.config-panel {
  .hint {
    font-size: 12px;
    color: #8c8c8c;
    margin-top: 4px;
  }

  .form-actions {
    display: flex;
    align-items: center;
    gap: 16px;

    .running-hint {
      color: #faad14;
      font-size: 13px;
    }
  }
}
</style>
