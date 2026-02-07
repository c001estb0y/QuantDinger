<template>
  <div class="strategy-panel">
    <a-spin :spinning="loading">
      <!-- Status Summary -->
      <div class="status-summary">
        <div class="status-item">
          <span class="status-label">运行状态</span>
          <a-tag :color="status.is_running ? 'green' : 'default'" class="status-tag">
            {{ status.is_running ? '运行中' : '已停止' }}
          </a-tag>
        </div>
        <div class="status-item">
          <span class="status-label">监控时段</span>
          <span class="status-value">{{ config.monitoring_start }} - {{ config.monitoring_end }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">今日信号</span>
          <span class="status-value highlight">{{ status.today_signal_count || 0 }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">当前持仓</span>
          <span class="status-value highlight">{{ status.open_position_count || 0 }} 手</span>
        </div>
      </div>

      <a-divider />

      <!-- Configuration Form -->
      <a-form
        ref="formRef"
        :model="formState"
        :label-col="{ span: 8 }"
        :wrapper-col="{ span: 16 }"
        size="small"
      >
        <!-- Thresholds -->
        <a-form-item label="买入阈值1">
<a-input-number
            v-model="formState.drop_threshold_1"
            :min="-10"
            :max="0"
            :step="0.5"
            :precision="1"
            addon-after="%"
            style="width: 100%"
          />
          <div class="form-hint">触发第一档买入的跌幅百分比</div>
        </a-form-item>

        <a-form-item label="买入阈值2">
<a-input-number
            v-model="formState.drop_threshold_2"
            :min="-10"
            :max="0"
            :step="0.5"
            :precision="1"
            addon-after="%"
            style="width: 100%"
          />
          <div class="form-hint">触发第二档买入的跌幅百分比</div>
        </a-form-item>

        <a-form-item label="最大持仓">
<a-input-number
            v-model="formState.max_position"
            :min="1"
            :max="10"
            :step="1"
            addon-after="手"
            style="width: 100%"
          />
        </a-form-item>

        <a-divider />

        <!-- Notification Channels -->
        <a-form-item label="通知渠道">
<a-checkbox-group v-model="formState.notification_channels">
            <a-row>
              <a-col :span="8">
                <a-checkbox value="browser">浏览器</a-checkbox>
              </a-col>
              <a-col :span="8">
                <a-checkbox value="telegram">Telegram</a-checkbox>
              </a-col>
              <a-col :span="8">
                <a-checkbox value="wechat">微信</a-checkbox>
              </a-col>
            </a-row>
          </a-checkbox-group>
        </a-form-item>

        <!-- Telegram Chat ID (conditional) -->
        <a-form-item
          v-if="formState.notification_channels.includes('telegram')"
          label="Telegram ID"
        >
<a-input
            v-model="formState.telegram_chat_id"
            placeholder="请输入 Chat ID"
          />
        </a-form-item>

        <!-- WeChat Webhook (conditional) -->
        <a-form-item
          v-if="formState.notification_channels.includes('wechat')"
          label="微信Webhook"
        >
<a-input
            v-model="formState.wechat_webhook"
            placeholder="请输入企业微信机器人 Webhook URL"
          />
        </a-form-item>

        <!-- Save Button -->
        <a-form-item :wrapper-col="{ offset: 8, span: 16 }">
<a-button type="primary" @click="handleSave" :loading="saving">
            <a-icon type="save" />
            保存配置
          </a-button>
        </a-form-item>
      </a-form>
    </a-spin>
  </div>
</template>

<script>
import { ref, reactive, watch } from 'vue'

export default {
  name: 'StrategyPanel',
  props: {
    config: {
      type: Object,
      default: () => ({
        symbols: ['IC0', 'IM0', 'IF0', 'IH0'],
        drop_threshold_1: -2.0,
        drop_threshold_2: -3.0,
        monitoring_start: '09:30',
        monitoring_end: '15:00',
        max_position: 1,
        notification_channels: ['browser'],
        telegram_chat_id: '',
        wechat_webhook: ''
      })
    },
    status: {
      type: Object,
      default: () => ({
        is_running: false,
        monitoring_start: '09:30',
        monitoring_end: '15:00',
        today_signal_count: 0,
        open_position_count: 0
      })
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['save'],
  setup (props, { emit }) {
    const saving = ref(false)

    const formState = reactive({
      drop_threshold_1: props.config.drop_threshold_1,
      drop_threshold_2: props.config.drop_threshold_2,
      max_position: props.config.max_position,
      notification_channels: [...(props.config.notification_channels || ['browser'])],
      telegram_chat_id: props.config.telegram_chat_id || '',
      wechat_webhook: props.config.wechat_webhook || ''
    })

    // Watch for config changes from parent
    watch(() => props.config, (newConfig) => {
      formState.drop_threshold_1 = newConfig.drop_threshold_1
      formState.drop_threshold_2 = newConfig.drop_threshold_2
      formState.max_position = newConfig.max_position
      formState.notification_channels = [...(newConfig.notification_channels || ['browser'])]
      formState.telegram_chat_id = newConfig.telegram_chat_id || ''
      formState.wechat_webhook = newConfig.wechat_webhook || ''
    }, { deep: true })

    const handleSave = async () => {
      saving.value = true
      try {
        emit('save', {
          drop_threshold_1: formState.drop_threshold_1,
          drop_threshold_2: formState.drop_threshold_2,
          max_position: formState.max_position,
          notification_channels: formState.notification_channels,
          telegram_chat_id: formState.telegram_chat_id,
          wechat_webhook: formState.wechat_webhook
        })
      } finally {
        saving.value = false
      }
    }

    return {
      formState,
      saving,
      handleSave
    }
  }
}
</script>

<style lang="less" scoped>
.strategy-panel {
  .status-summary {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;

    .status-item {
      display: flex;
      flex-direction: column;

      .status-label {
        font-size: 12px;
        color: #8c8c8c;
        margin-bottom: 4px;
      }

      .status-value {
        font-size: 14px;
        color: #262626;

        &.highlight {
          font-weight: 600;
          color: #1890ff;
        }
      }

      .status-tag {
        width: fit-content;
      }
    }
  }

  .form-hint {
    font-size: 11px;
    color: #bfbfbf;
    margin-top: 2px;
  }
}
</style>
