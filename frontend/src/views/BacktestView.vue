<template>
  <div class="backtest-view">
    <el-card class="welcome-card">
      <template #header>
        <h2>策略回测</h2>
      </template>
      <el-result
        icon="info"
        title="功能开发中"
        sub-title="策略回测功能正在开发中，敬请期待..."
      >
        <template #extra>
          <el-button type="primary" @click="testAPI">测试API连接</el-button>
        </template>
      </el-result>

      <el-alert
        v-if="apiStatus.connected"
        title="API连接成功"
        type="success"
        :description="`已连接到 ${apiStatus.apiUrl}`"
        show-icon
        :closable="false"
        style="margin-top: 20px"
      />

      <el-alert
        v-if="apiStatus.error"
        title="API连接失败"
        type="error"
        :description="apiStatus.error"
        show-icon
        :closable="false"
        style="margin-top: 20px"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '@/api/client'

const apiStatus = ref({
  connected: false,
  error: null,
  apiUrl: ''
})

const testAPI = async () => {
  try {
    apiStatus.value.error = null
    const result = await api.healthCheck()
    apiStatus.value.connected = true
    apiStatus.value.apiUrl = import.meta.env.VITE_API_BASE_URL
    console.log('API健康检查成功:', result)
  } catch (error) {
    apiStatus.value.connected = false
    apiStatus.value.error = error.message
    console.error('API连接失败:', error)
  }
}
</script>

<style scoped>
.backtest-view {
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-card {
  text-align: center;
}
</style>
