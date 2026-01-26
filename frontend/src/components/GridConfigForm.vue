<template>
  <div class="grid-config-form">
    <el-form :model="formData" :rules="rules" ref="formRef" label-width="140px">
      <!-- ETF选择 -->
      <el-form-item label="ETF代码" prop="etf_code">
        <el-input
          v-model="formData.etf_code"
          placeholder="请输入ETF代码，如 560590.SH"
          clearable
        />
      </el-form-item>

      <!-- 基准价格 -->
      <el-form-item label="基准价格" prop="base_price">
        <el-input-number
          v-model="formData.base_price"
          :precision="3"
          :step="0.001"
          :min="0"
          controls-position="right"
          style="width: 200px"
        />
        <el-button
          type="primary"
          link
          style="margin-left: 10px"
          @click="fetchCurrentPrice"
          :loading="loadingPrice"
        >
          获取当前价格
        </el-button>
      </el-form-item>

      <!-- 网格间距 -->
      <el-form-item label="上涨网格间距" prop="grid_spacing_up">
        <el-input-number
          v-model="formData.grid_spacing_up"
          :precision="1"
          :step="0.5"
          :min="0.1"
          :max="100"
          controls-position="right"
          style="width: 200px"
        />
        <span style="margin-left: 10px">%</span>
      </el-form-item>

      <el-form-item label="下跌网格间距" prop="grid_spacing_down">
        <el-input-number
          v-model="formData.grid_spacing_down"
          :precision="1"
          :step="0.5"
          :min="-100"
          :max="-0.1"
          controls-position="right"
          style="width: 200px"
        />
        <span style="margin-left: 10px">%</span>
      </el-form-item>

      <!-- 买卖数量配置 -->
      <el-form-item label="数量类型" prop="buy_amount_type">
        <el-radio-group v-model="formData.buy_amount_type">
          <el-radio label="shares">按份额</el-radio>
          <el-radio label="currency">按金额</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="买入数量" prop="buy_amount">
        <el-input-number
          v-model="formData.buy_amount"
          :precision="0"
          :step="1000"
          :min="1"
          controls-position="right"
          style="width: 200px"
        />
        <span style="margin-left: 10px">{{ formData.buy_amount_type === 'shares' ? '份' : '元' }}</span>
      </el-form-item>

      <el-form-item label="卖出数量" prop="sell_amount">
        <el-input-number
          v-model="formData.sell_amount"
          :precision="0"
          :step="1000"
          :min="1"
          controls-position="right"
          style="width: 200px"
        />
        <span style="margin-left: 10px">{{ formData.sell_amount_type === 'shares' ? '份' : '元' }}</span>
      </el-form-item>

      <!-- 网格预览 -->
      <el-form-item label="网格预览">
        <div ref="chartRef" style="width: 100%; height: 300px"></div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

// Props
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['update:modelValue'])

// 表单数据
const formData = reactive({
  etf_code: props.modelValue.etf_code || '560590.SH',
  etf_name: props.modelValue.etf_name || '',
  base_price: props.modelValue.base_price || 1.573,
  grid_spacing_up: props.modelValue.grid_spacing_up || 5.0,
  grid_spacing_down: props.modelValue.grid_spacing_down || -5.0,
  buy_amount: props.modelValue.buy_amount || 80000,
  sell_amount: props.modelValue.sell_amount || 80000,
  buy_amount_type: props.modelValue.buy_amount_type || 'shares',
  sell_amount_type: props.modelValue.sell_amount_type || 'shares',
})

// 表单引用
const formRef = ref(null)

// 加载状态
const loadingPrice = ref(false)

// 图表引用
const chartRef = ref(null)
let chart = null

// 验证规则
const rules = {
  etf_code: [
    { required: true, message: '请输入ETF代码', trigger: 'blur' }
  ],
  base_price: [
    { required: true, message: '请输入基准价格', trigger: 'blur' },
    { type: 'number', min: 0.001, message: '基准价格必须大于0', trigger: 'blur' }
  ],
  grid_spacing_up: [
    { required: true, message: '请输入上涨网格间距', trigger: 'blur' }
  ],
  grid_spacing_down: [
    { required: true, message: '请输入下跌网格间距', trigger: 'blur' }
  ],
  buy_amount: [
    { required: true, message: '请输入买入数量', trigger: 'blur' }
  ],
  sell_amount: [
    { required: true, message: '请输入卖出数量', trigger: 'blur' }
  ]
}

// 监听数据变化，同步到父组件
watch(formData, (newVal) => {
  emit('update:modelValue', { ...newVal })
}, { deep: true })

// 获取当前价格
const fetchCurrentPrice = async () => {
  if (!formData.etf_code) {
    ElMessage.warning('请先输入ETF代码')
    return
  }

  loadingPrice.value = true
  try {
    // 调用API获取当前价格
    const response = await api.market.getCurrentPrice(formData.etf_code)
    formData.base_price = response.price
    ElMessage.success(`获取当前价格成功: ${response.price}`)
  } catch (error) {
    console.error('获取当前价格失败:', error)
    ElMessage.error(`获取当前价格失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    loadingPrice.value = false
  }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)
  updateChart()

  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    chart?.resize()
  })
}

// 更新图表
const updateChart = () => {
  if (!chart) return

  // 计算网格价格
  const basePrice = formData.base_price
  const gridSpacingUp = formData.grid_spacing_up / 100
  const gridSpacingDown = formData.grid_spacing_down / 100

  const buyPrices = []
  const sellPrices = []
  const buyVolumes = []
  const sellVolumes = []

  // 生成5层网格
  for (let i = 1; i <= 5; i++) {
    // 买入网格（向下）
    const buyPrice = basePrice * (1 + gridSpacingDown * i)
    buyPrices.push(buyPrice.toFixed(3))
    buyVolumes.push(formData.buy_amount)

    // 卖出网格（向上）
    const sellPrice = basePrice * (1 + gridSpacingUp * i)
    sellPrices.push(sellPrice.toFixed(3))
    sellVolumes.push(formData.sell_amount)
  }

  const option = {
    title: {
      text: '网格交易预览',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['买入网格', '卖出网格'],
      top: 30
    },
    xAxis: {
      type: 'category',
      data: ['第1层', '第2层', '第3层', '第4层', '第5层']
    },
    yAxis: {
      type: 'value',
      name: '价格',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '买入网格',
        type: 'bar',
        data: buyPrices,
        itemStyle: {
          color: '#52c41a'
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}'
        }
      },
      {
        name: '卖出网格',
        type: 'bar',
        data: sellPrices,
        itemStyle: {
          color: '#ff4d4f'
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}'
        }
      }
    ]
  }

  chart.setOption(option)
}

// 监听关键参数变化，更新图表
watch([
  () => formData.base_price,
  () => formData.grid_spacing_up,
  () => formData.grid_spacing_down
], () => {
  updateChart()
})

// 表单验证
const validateForm = () => {
  return formRef.value?.validate()
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
}

// 暴露方法给父组件
defineExpose({
  validateForm,
  resetForm
})

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.grid-config-form {
  padding: 20px;
}
</style>
