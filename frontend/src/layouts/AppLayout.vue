<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, Monitor, Setting, FolderOpened, Cpu } from '@element-plus/icons-vue'
import { navGroups } from '@/nav'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isDevMode = import.meta.env.DEV || String(import.meta.env.VITE_DEV_MODE || '').toLowerCase() === 'true'

const activeMenu = computed(() => route.path)
const role = computed(() => (auth.role || 'user').toLowerCase())
const visibleNavGroups = computed(() =>
  navGroups
    .map((group) => ({
      ...group,
      children: group.children.filter(
        (child) => (!child.roles || child.roles.includes(role.value)) && (!child.devOnly || isDevMode),
      ),
    }))
    .filter((group) => group.children.length > 0)
)

const groupIcon = (title: string) => {
  const map: Record<string, typeof Setting> = {
    总览: DataAnalysis,
    调度中心: Setting,
    分析中心: Monitor,
    数据与治理: FolderOpened,
    账户: Cpu,
  }
  return map[title] ?? Setting
}

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-cn">茧评</div>
        <div class="brand-en">Jianping · Cocoon insight</div>
      </div>

      <el-scrollbar class="nav-scroll">
        <el-menu :default-active="activeMenu" router class="side-menu" :collapse="false">
          <el-sub-menu v-for="g in visibleNavGroups" :key="g.title" :index="g.title">
            <template #title>
              <el-icon class="sub-icon">
                <component :is="groupIcon(g.title)" />
              </el-icon>
              <span>{{ g.title }}</span>
            </template>
            <el-menu-item v-for="c in g.children" :key="c.path" :index="c.path">
              {{ c.title }}
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-footer">
        <div class="user">
          <el-avatar :size="36" class="avatar">{{ (auth.username || '?').slice(0, 1) }}</el-avatar>
          <div class="user-meta">
            <div class="user-name">{{ auth.username || '用户' }}</div>
            <div class="user-role">{{ auth.role || '—' }}</div>
          </div>
        </div>
        <div class="footer-actions">
          <el-button class="pwd-btn" link type="primary" @click="router.push('/app/account/change-password')">
            修改密码
          </el-button>
          <el-button class="logout-btn" @click="logout">退出登录</el-button>
        </div>
      </div>
    </aside>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  min-height: 100vh;
}

.sidebar {
  width: 248px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-right: 1px solid #e2e8f0;
}

.brand {
  padding: 20px 18px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.brand-cn {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
}

.brand-en {
  margin-top: 4px;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.3;
}

.nav-scroll {
  flex: 1;
  min-height: 0;
}

.side-menu {
  border-right: none;
  background: transparent;
  padding: 8px 0;
}

.side-menu :deep(.el-sub-menu__title:hover),
.side-menu :deep(.el-menu-item:hover) {
  background-color: rgba(139, 92, 246, 0.06);
}

.side-menu :deep(.el-menu-item.is-active) {
  background: rgba(139, 92, 246, 0.12);
  color: #6d28d9;
  border-radius: 8px;
  margin: 0 8px;
  width: calc(100% - 16px);
}

.sub-icon {
  margin-right: 8px;
}

.sidebar-footer {
  padding: 14px 14px 18px;
  border-top: 1px solid #e2e8f0;
}

.user {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.avatar {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: #fff;
  font-weight: 600;
}

.user-meta {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 0.75rem;
  color: #64748b;
}

.footer-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pwd-btn {
  width: 100%;
  justify-content: center;
}

.logout-btn {
  width: 100%;
}

.main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: #f8f9fa;
  padding: 24px 28px 32px;
}
</style>
