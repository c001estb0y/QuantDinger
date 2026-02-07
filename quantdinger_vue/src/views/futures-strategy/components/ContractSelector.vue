<template>
  <div class="contract-selector">
<a-checkbox-group
      v-model="internalSelectedSymbols"
      @change="handleChange"
    >
      <a-row :gutter="[16, 8]">
        <a-col v-for="contract in contracts" :key="contract.symbol" :xs="12" :sm="6">
          <a-checkbox :value="contract.symbol" class="contract-checkbox">
            <div class="contract-info">
              <span class="contract-symbol">{{ contract.symbol }}</span>
              <span class="contract-name">{{ contract.name }}</span>
            </div>
          </a-checkbox>
        </a-col>
      </a-row>
    </a-checkbox-group>

    <!-- Fallback when no contracts loaded -->
    <a-row v-if="!contracts || contracts.length === 0" :gutter="[16, 8]">
      <a-col v-for="symbol in defaultSymbols" :key="symbol" :xs="12" :sm="6">
        <a-checkbox
          :checked="internalSelectedSymbols.includes(symbol)"
          @change="(e) => handleSingleChange(symbol, e.target.checked)"
          class="contract-checkbox"
        >
          <div class="contract-info">
            <span class="contract-symbol">{{ symbol }}</span>
            <span class="contract-name">{{ getDefaultName(symbol) }}</span>
          </div>
        </a-checkbox>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'ContractSelector',
  props: {
    selectedSymbols: {
      type: Array,
      default: () => ['IC0', 'IM0', 'IF0', 'IH0']
    },
    contracts: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:selectedSymbols', 'change'],
  setup (props, { emit }) {
    const defaultSymbols = ['IC0', 'IM0', 'IF0', 'IH0']

    const defaultNames = {
      'IC0': '中证500',
      'IM0': '中证1000',
      'IF0': '沪深300',
      'IH0': '上证50'
    }

    const internalSelectedSymbols = ref([...props.selectedSymbols])

    // Watch for external changes
    watch(() => props.selectedSymbols, (newVal) => {
      internalSelectedSymbols.value = [...newVal]
    }, { deep: true })

    const handleChange = (checkedValues) => {
      emit('update:selectedSymbols', checkedValues)
      emit('change', checkedValues)
    }

    const handleSingleChange = (symbol, checked) => {
      let newValues = [...internalSelectedSymbols.value]
      if (checked && !newValues.includes(symbol)) {
        newValues.push(symbol)
      } else if (!checked) {
        newValues = newValues.filter(s => s !== symbol)
      }
      internalSelectedSymbols.value = newValues
      emit('update:selectedSymbols', newValues)
      emit('change', newValues)
    }

    const getDefaultName = (symbol) => {
      return defaultNames[symbol] || symbol
    }

    return {
      defaultSymbols,
      internalSelectedSymbols,
      handleChange,
      handleSingleChange,
      getDefaultName
    }
  }
}
</script>

<style lang="less" scoped>
.contract-selector {
  .contract-checkbox {
    width: 100%;
    padding: 8px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    transition: all 0.3s;

    &:hover {
      border-color: #1890ff;
    }

    :deep(.ant-checkbox-checked) + span {
      .contract-info {
        .contract-symbol {
          color: #1890ff;
        }
      }
    }
  }

  .contract-info {
    display: flex;
    flex-direction: column;
    line-height: 1.4;

    .contract-symbol {
      font-weight: 600;
      font-size: 14px;
      color: #262626;
    }

    .contract-name {
      font-size: 12px;
      color: #8c8c8c;
    }
  }
}
</style>
