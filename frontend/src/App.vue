<template>
  <div id="app">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-content">
          <h1 class="title">QMT量化交易系统</h1>
          <el-menu
            :default-active="activeMenu"
            mode="horizontal"
            :ellipsis="false"
            router
            class="menu"
          >
            <el-menu-item index="/backtest">策略回测</el-menu-item>
            <el-menu-item index="/optimization">参数优化</el-menu-item>
            <el-menu-item index="/monitor">实盘监控</el-menu-item>
          </el-menu>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #409eff;
  color: white;
  padding: 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 0 20px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: white;
}

.menu {
  background-color: transparent;
  border: none;
}

.menu .el-menu-item {
  color: white;
  font-size: 16px;
}

.menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.menu .el-menu-item.is-active {
  background-color: rgba(255, 255, 255, 0.2);
  border-bottom-color: white;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
