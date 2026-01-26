import axios from 'axios'

// 创建axios实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)

// API接口定义
export const api = {
  // 健康检查
  healthCheck: () => apiClient.get('/health'),

  // 回测相关
  backtest: {
    run: (config) => apiClient.post('/api/backtest/run', config),
    getTask: (taskId) => apiClient.get(`/api/backtest/tasks/${taskId}`),
    listTasks: () => apiClient.get('/api/backtest/tasks')
  },

  // 市场数据相关
  market: {
    getCurrentPrice: (etfCode) => apiClient.get(`/api/market/current-price/${etfCode}`),
    getBatchPrices: (etfCodes) => apiClient.post('/api/market/batch-prices', etfCodes)
  },

  // 优化相关
  optimization: {
    run: (config) => apiClient.post('/api/optimization/run', config),
    getResult: (taskId) => apiClient.get(`/api/optimization/results/${taskId}`),
    recommend: (config) => apiClient.post('/api/optimization/recommend', config)
  },

  // 监控相关
  monitor: {
    getAccount: () => apiClient.get('/api/monitor/account'),
    getStrategy: (strategyId) => apiClient.get(`/api/monitor/strategy/${strategyId}`)
  }
}

export default apiClient
