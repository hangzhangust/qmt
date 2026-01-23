<template>
  <div class="all-weather-config-form">
    <el-form :model="localConfig" label-width="120px">

      <!-- 仓位比例 -->
      <el-form-item label="仓位比例">
        <el-slider
          v-model="localConfig.position_ratio"
          :min="0.1"
          :max="1.0"
          :step="0.1"
          :format-tooltip="val => `${(val * 100).toFixed(0)}%`"
          style="width: 80%"
        />
        <span style="margin-left: 10px">
          {{ (localConfig.position_ratio * 100).toFixed(0) }}%
        </span>
      </el-form-item>

      <!-- 再平衡周期 -->
      <el-form-item label="再平衡周期">
        <el-input-number
          v-model="localConfig.rebalance_period"
          :min="1"
          :max="365"
          :step="1"
          controls-position="right"
          style="width: 200px"
        />
        <span style="margin-left: 10px">天</span>
        <div style="color: #909399; font-size: 12px; margin-top: 5px">
          超过该天数将触发再平衡
        </div>
      </el-form-item>

      <!-- 再平衡阈值 -->
      <el-form-item label="再平衡阈值">
        <el-slider
          v-model="localConfig.rebalance_threshold"
          :min="0.01"
          :max="0.30"
          :step="0.01"
          :format-tooltip="val => `${(val * 100).toFixed(0)}%`"
          style="width: 80%"
        />
        <span style="margin-left: 10px">
          {{ (localConfig.rebalance_threshold * 100).toFixed(0) }}%
        </span>
        <div style="color: #909399; font-size: 12px; margin-top: 5px">
          配置偏离目标超过该阈值时触发再平衡
        </div>
      </el-form-item>

      <!-- 高级选项：自定义资产配置 -->
      <el-divider content-position="left">高级选项</el-divider>

      <el-form-item label="自定义配置">
        <el-switch
          v-model="useCustomAllocation"
          active-text="开启"
          inactive-text="关闭"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 5px">
          开启后可自定义四类资产的ETF标的
        </div>
      </el-form-item>

      <!-- 自定义资产配置表单（可选） -->
      <div v-if="useCustomAllocation" class="custom-allocation">
        <el-alert
          title="默认配置"
          type="info"
          :closable="false"
          style="margin-bottom: 15px"
        >
          <template #default>
            <div style="font-size: 12px">
              <p>• 商品类: 518880.SH (黄金ETF)</p>
              <p>• 股票类: 159915.SZ, 513100.SH, 513520.SH</p>
              <p>• 长债类: 511260.SH, 511010.SH</p>
              <p>• 短债类: 511360.SH</p>
            </div>
          </template>
        </el-alert>

        <el-form-item label="商品类ETF">
          <el-input
            v-model="customAllocation.commodities"
            placeholder="518880.SH"
            style="width: 300px"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            多个ETF用逗号分隔，如：518880.SH,159930.SH
          </div>
        </el-form-item>

        <el-form-item label="股票类ETF">
          <el-input
            v-model="customAllocation.stocks"
            placeholder="159915.SZ,513100.SH,513520.SH"
            style="width: 500px"
          />
        </el-form-item>

        <el-form-item label="长债类ETF">
          <el-input
            v-model="customAllocation.long_bonds"
            placeholder="511260.SH,511010.SH"
            style="width: 400px"
          />
        </el-form-item>

        <el-form-item label="短债类ETF">
          <el-input
            v-model="customAllocation.short_bonds"
            placeholder="511360.SH"
            style="width: 300px"
          />
        </el-form-item>
      </div>

    </el-form>

    <!-- 配置预览 -->
    <el-divider content-position="left">配置预览</el-divider>
    <div class="config-preview">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="仓位比例">
          {{ (localConfig.position_ratio * 100).toFixed(0) }}%
        </el-descriptions-item>
        <el-descriptions-item label="再平衡周期">
          {{ localConfig.rebalance_period }}天
        </el-descriptions-item>
        <el-descriptions-item label="再平衡阈值">
          {{ (localConfig.rebalance_threshold * 100).toFixed(0) }}%
        </el-descriptions-item>
        <el-descriptions-item label="资产配置">
          {{ useCustomAllocation ? '自定义' : '默认（四类等权25%）' }}
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="useCustomAllocation" style="margin-top: 15px; font-size: 12px; color: #606266">
        <div>• 商品类: {{ customAllocation.commodities || '未配置' }}</div>
        <div>• 股票类: {{ customAllocation.stocks || '未配置' }}</div>
        <div>• 长债类: {{ customAllocation.long_bonds || '未配置' }}</div>
        <div>• 短债类: {{ customAllocation.short_bonds || '未配置' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

// 本地配置
const localConfig = ref({ ...props.modelValue })

// 是否使用自定义配置
const useCustomAllocation = ref(false)

// 自定义资产配置
const customAllocation = ref({
  commodities: '',
  stocks: '',
  long_bonds: '',
  short_bonds: ''
})

// 监听配置变化
watch(localConfig, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

// 监听自定义配置开关
watch(useCustomAllocation, (newVal) => {
  if (newVal) {
    // 开启自定义配置
    localConfig.value.custom_allocation = {
      commodities: {
        target_weight: 0.25,
        etfs: customAllocation.value.commodities.split(',').map(s => s.trim()).filter(s => s),
        names: {}
      },
      stocks: {
        target_weight: 0.25,
        etfs: customAllocation.value.stocks.split(',').map(s => s.trim()).filter(s => s),
        names: {}
      },
      long_bonds: {
        target_weight: 0.25,
        etfs: customAllocation.value.long_bonds.split(',').map(s => s.trim()).filter(s => s),
        names: {}
      },
      short_bonds: {
        target_weight: 0.25,
        etfs: customAllocation.value.short_bonds.split(',').map(s => s.trim()).filter(s => s),
        names: {}
      }
    }
  } else {
    // 关闭自定义配置，使用默认配置
    localConfig.value.custom_allocation = null
  }
}, { deep: true })

// 初始化
if (props.modelValue.custom_allocation) {
  useCustomAllocation.value = true
  // 从已有的自定义配置中提取ETF代码
  const alloc = props.modelValue.custom_allocation
  if (alloc.commodities?.etfs) {
    customAllocation.value.commodities = alloc.commodities.etfs.join(',')
  }
  if (alloc.stocks?.etfs) {
    customAllocation.value.stocks = alloc.stocks.etfs.join(',')
  }
  if (alloc.long_bonds?.etfs) {
    customAllocation.value.long_bonds = alloc.long_bonds.etfs.join(',')
  }
  if (alloc.short_bonds?.etfs) {
    customAllocation.value.short_bonds = alloc.short_bonds.etfs.join(',')
  }
}
</script>

<style scoped>
.all-weather-config-form {
  padding: 10px;
}

.custom-allocation {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
  margin-top: 10px;
}

.config-preview {
  background: #f0f9ff;
  padding: 15px;
  border-radius: 4px;
}

.el-form-item {
  margin-bottom: 18px;
}
</style>
