import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/backtest'
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('@/views/BacktestView.vue'),
    meta: { title: '策略回测' }
  },
  {
    path: '/optimization',
    name: 'Optimization',
    component: () => import('@/views/OptimizationView.vue'),
    meta: { title: '参数优化' }
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: () => import('@/views/MonitorView.vue'),
    meta: { title: '实盘监控' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || 'QMT量化交易系统'} - QMT`
  next()
})

export default router
