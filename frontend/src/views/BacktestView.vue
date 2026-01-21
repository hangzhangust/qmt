<template>
  <div class="backtest-view">
    <el-row :gutter="20">
      <!-- 左侧：配置区域 -->
      <el-col :span="12">
        <el-card class="config-card">
          <template #header>
            <h3>回测配置</h3>
          </template>

          <!-- 策略选择 -->
          <el-form :model="backtestConfig" label-width="100px" style="margin-bottom: 20px">
            <el-form-item label="策略类型">
              <el-select v-model="strategyType" style="width: 100%">
                <el-option label="网格交易策略" value="grid" />
                <el-option label="全天候策略" value="all_weather" disabled />
              </el-select>
            </el-form-item>
          </el-form>

          <!-- 网格策略配置 -->
          <div v-if="strategyType === 'grid'">
            <h4 style="margin-bottom: 15px">网格策略参数</h4>
            <GridConfigForm
              ref="gridConfigFormRef"
              v-model="gridConfig"
            />
          </div>

          <!-- 回测参数 -->
          <h4 style="margin: 20px 0 15px 0">回测参数</h4>
          <el-form :model="backtestConfig" :rules="backtestRules" ref="backtestFormRef" label-width="100px">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker
                v-model="startDate"
                type="date"
                placeholder="选择开始日期"
                format="YYYY-MM-DD"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="结束日期" prop="end_date">
              <el-date-picker
                v-model="endDate"
                type="date"
                placeholder="选择结束日期"
                format="YYYY-MM-DD"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="初始资金" prop="initial_cash">
              <el-input-number
                v-model="backtestConfig.initial_cash"
                :step="100000"
                :min="10000"
                :precision="0"
                controls-position="right"
                style="width: 100%"
              />
              <span style="margin-left: 10px">元</span>
            </el-form-item>
          </el-form>

          <!-- 操作按钮 -->
          <div style="margin-top: 20px; text-align: center">
            <el-button
              type="primary"
              size="large"
              @click="startBacktest"
              :loading="isRunning"
              :disabled="isRunning"
            >
              {{ isRunning ? '回测运行中...' : '开始回测' }}
            </el-button>
            <el-button
              v-if="isRunning"
              type="danger"
              size="large"
              @click="stopBacktest"
            >
              停止回测
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：进度和结果 -->
      <el-col :span="12">
        <!-- 进度显示 -->
        <el-card v-if="isRunning || backtestResult" class="result-card" style="margin-bottom: 20px">
          <template #header>
            <h3>回测进度</h3>
          </template>

          <div v-if="isRunning">
            <el-progress
              :percentage="progress"
              :status="progressStatus"
              style="margin-bottom: 20px"
            />
            <el-alert
              :title="progressMessage"
              :type="progressStatus === 'exception' ? 'error' : 'info'"
              :closable="false"
            />
          </div>

          <div v-if="backtestResult && !isRunning">
            <el-result
              :icon="backtestResult.error ? 'error' : 'success'"
              :title="backtestResult.error ? '回测失败' : '回测完成'"
            >
              <template #sub-title>
                <div v-if="backtestResult.error">
                  {{ backtestResult.error }}
                </div>
                <div v-else>
                  <p>任务ID: {{ currentTaskId }}</p>
                  <p>最终资产: ¥{{ formatNumber(backtestResult.final_value) }}</p>
                  <p>总收益率: {{ backtestResult.total_return?.toFixed(2) }}%</p>
                </div>
              </template>
            </el-result>
          </div>
        </el-card>

        <!-- 结果展示 -->
        <el-card v-if="backtestResult && !backtestResult.error" class="result-card">
          <template #header>
            <h3>回测结果</h3>
          </template>

          <!-- 关键指标 -->
          <el-row :gutter="10" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-statistic title="最终资产" :value="backtestResult.final_value" :precision="2" prefix="¥" />
            </el-col>
            <el-col :span="12">
              <el-statistic title="总收益率" :value="backtestResult.total_return" :precision="2" suffix="%" />
            </el-col>
          </el-row>

          <el-row :gutter="10" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-statistic title="夏普比率" :value="backtestResult.sharpe_ratio" :precision="2" />
            </el-col>
            <el-col :span="12">
              <el-statistic title="最大回撤" :value="backtestResult.max_drawdown" :precision="2" suffix="%" />
            </el-col>
          </el-row>

          <el-row :gutter="10" style="margin-bottom: 20px">
            <el-col :span="8">
              <el-statistic title="网格触发次数" :value="backtestResult.total_grid_triggers" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="买入触发" :value="backtestResult.buy_triggers" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="卖出触发" :value="backtestResult.sell_triggers" />
            </el-col>
          </el-row>

          <!-- 详细结果折叠面板 -->
          <el-collapse>
            <el-collapse-item title="网格触发历史" name="triggers">
              <el-table
                :data="backtestResult.grid_triggers || []"
                stripe
                style="width: 100%"
                max-height="300"
              >
                <el-table-column prop="date" label="日期" width="120" />
                <el-table-column prop="action" label="操作" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.action === 'buy' ? 'success' : 'danger'">
                      {{ scope.row.action === 'buy' ? '买入' : '卖出' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="price" label="价格" width="100">
                  <template #default="scope">
                    {{ scope.row.price?.toFixed(3) }}
                  </template>
                </el-table-column>
                <el-table-column prop="shares" label="数量" width="100" />
                <el-table-column prop="amount" label="金额" width="120">
                  <template #default="scope">
                    {{ formatNumber(scope.row.amount) }}
                  </template>
                </el-table-column>
                <el-table-column prop="grid_level" label="网格层级" width="100" />
              </el-table>
            </el-collapse-item>
          </el-collapse>

          <!-- 导出按钮 -->
          <div style="margin-top: 20px; text-align: center">
            <el-button @click="exportResult">导出结果</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import GridConfigForm from '@/components/GridConfigForm.vue'
import { api } from '@/api/client'

// 策略类型
const strategyType = ref('grid')

// 网格配置
const gridConfig = ref({
  etf_code: '560590.SH',
  etf_name: '1000鹏华',
  base_price: 1.573,
  grid_spacing_up: 5.0,
  grid_spacing_down: -5.0,
  buy_amount: 80000,
  sell_amount: 80000,
  buy_amount_type: 'shares',
  sell_amount_type: 'shares',
})

// 回测配置
const backtestConfig = reactive({
  start_date: '20240101',
  end_date: '20260121',
  initial_cash: 1000000,
})

// 日期（用于日期选择器）
const startDate = ref('2024-01-01')
const endDate = ref('2026-01-21')

// 监听日期变化
watch([startDate, endDate], () => {
  backtestConfig.start_date = startDate.value
  backtestConfig.end_date = endDate.value
})

// 表单引用
const gridConfigFormRef = ref(null)
const backtestFormRef = ref(null)

// 回测规则
const backtestRules = {
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  initial_cash: [{ required: true, message: '请输入初始资金', trigger: 'blur' }],
}

// 运行状态
const isRunning = ref(false)
const progress = ref(0)
const progressMessage = ref('')
const progressStatus = ref('success')

// 结果
const currentTaskId = ref('')
const backtestResult = ref(null)

// WebSocket连接
let ws = null

// 启动回测
const startBacktest = async () => {
  try {
    // 验证表单
    await gridConfigFormRef.value?.validateForm()
    await backtestFormRef.value?.validate()

    // 清空之前的结果
    backtestResult.value = null
    isRunning.value = true
    progress.value = 0
    progressMessage.value = '正在启动回测...'

    // 调用API启动回测
    const response = await api.backtest.run({
      strategy_type: strategyType.value,
      strategy_config: gridConfig.value,
      backtest_config: backtestConfig,
    })

    currentTaskId.value = response.task_id
    ElMessage.success(`回测任务已启动: ${response.task_id}`)

    // 建立WebSocket连接
    connectWebSocket(response.task_id)

  } catch (error) {
    console.error('启动回测失败:', error)
    ElMessage.error(`启动回测失败: ${error.message || error}`)
    isRunning.value = false
  }
}

// 停止回测
const stopBacktest = () => {
  if (ws) {
    ws.close()
    ws = null
  }
  isRunning.value = false
  progress.value = 0
  progressMessage.value = '回测已停止'
  ElMessage.info('回测已停止')
}

// 建立WebSocket连接
const connectWebSocket = (taskId) => {
  const wsUrl = `ws://localhost:8000/api/backtest/ws/${taskId}`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket连接成功')
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    console.log('WebSocket收到消息:', data)

    if (data.type === 'connected') {
      progressMessage.value = '连接成功，准备开始回测...'
    } else if (data.type === 'task_update') {
      const task = data.data
      progress.value = task.progress || 0
      progressMessage.value = task.message || '回测中...'

      if (task.status === 'completed') {
        isRunning.value = false
        backtestResult.value = task.result
        ElMessage.success('回测完成')
        ws.close()
      } else if (task.status === 'failed') {
        isRunning.value = false
        backtestResult.value = { error: task.error }
        progressStatus.value = 'exception'
        ElMessage.error('回测失败')
        ws.close()
      }
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
    progressStatus.value = 'exception'
    progressMessage.value = '连接错误'
  }

  ws.onclose = () => {
    console.log('WebSocket连接关闭')
  }
}

// 导出结果
const exportResult = () => {
  if (!backtestResult.value) return

  const data = JSON.stringify(backtestResult.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `backtest_result_${currentTaskId.value}.json`
  link.click()
  URL.revokeObjectURL(url)

  ElMessage.success('结果已导出')
}

// 格式化数字
const formatNumber = (num) => {
  if (num === null || num === undefined) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 生命周期
onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.backtest-view {
  max-width: 1400px;
  margin: 0 auto;
}

.config-card,
.result-card {
  min-height: 400px;
}

h3, h4 {
  margin: 0;
  font-weight: 600;
}
</style>
