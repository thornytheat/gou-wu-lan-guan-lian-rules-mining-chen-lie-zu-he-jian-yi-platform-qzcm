<template>
  <div class="shell">
    <aside class="rail">
      <div class="rail__brand">
        <div class="rail__endcap">
          <span class="rail__endcap-mark">拾光</span>
          <span class="rail__endcap-sub">便利店 · 品类运营中心</span>
        </div>
        <div class="rail__wordmark">
          <span class="rail__name">basketrule</span>
          <span class="eyebrow">basket · affinity · planogram</span>
        </div>
      </div>

      <div class="rail__scope">
        <div class="label">试点范围</div>
        <div class="rail__scope-line">
          <span class="tag-num">12</span> 家门店 · <span class="tag-num">40</span> 个 SKU
        </div>
        <div class="rail__scope-sub">3,000 张小票 / 7 天样本</div>
      </div>

      <nav class="rail__nav">
        <div class="eyebrow rail__nav-title">关联陈列链路</div>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="peg" active-class="is-active">
          <span class="peg__no">{{ item.no }}</span>
          <span class="peg__body">
            <span class="peg__label">{{ item.label }}</span>
            <span class="peg__hint">{{ item.hint }}</span>
          </span>
        </RouterLink>
      </nav>

      <div class="rail__foot">
        <div class="rail__user">
          <div>
            <div class="rail__user-name">{{ auth.displayName || '未登录' }}</div>
            <div class="rail__user-mail">{{ auth.email }}</div>
          </div>
          <span class="chip chip--mint">{{ ROLE_LABELS[auth.role] }}</span>
        </div>
        <button class="btn btn--quiet rail__logout" data-test="logout" @click="logout">
          退出登录
        </button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="topbar__left">
          <span class="label">{{ route.meta.section ?? '品类运营中心' }}</span>
          <span class="topbar__slash">/</span>
          <span class="topbar__page">{{ route.meta.title ?? '工作台' }}</span>
        </div>
        <div class="topbar__right">
          <span class="topbar__meta">W45 · 2026</span>
          <span class="topbar__meta">apriori 1.0.0</span>
          <span class="topbar__dot" />
        </div>
      </header>
      <div class="body">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/authStore'
import { ROLE_LABELS } from '../../constants/roles'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = computed(() => {
  const items = [
    ...(auth.can('baskets:read')
      ? [{ to: '/ingest', no: '00', label: '补传核对', hint: '接收 · 重复 · 作废 · 更正' }]
      : []),
    { to: '/mining', no: '01', label: '规则挖掘', hint: '参数 · 频繁项集' },
    { to: '/rules', no: '02', label: '规则复核', hint: '筛选 · 采纳 · 稳定性' },
    { to: '/planogram', no: '03', label: '陈列建议', hint: '货架位 · 增量 · 工单' },
  ]
  return items
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--rail) minmax(0, 1fr);
  min-height: 100vh;
}

.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--shelf-soft);
  background: var(--paper-2);
  padding: 18px 16px 16px;
}

/* 端架头：薄荷绿价签带 */
.rail__endcap {
  background: var(--mint);
  border: 1px solid var(--mint-deep);
  padding: 9px 11px 8px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  box-shadow: inset 0 -3px 0 oklch(50% 0.08 168 / 0.25);
}
.rail__endcap-mark {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--mint-ink);
}
.rail__endcap-sub {
  font-size: 9.5px;
  letter-spacing: 0.1em;
  color: var(--mint-ink);
  opacity: 0.8;
}
.rail__wordmark {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rail__name {
  font-family: var(--tag-font);
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
}

.rail__scope {
  margin-top: 14px;
  padding: 9px 0 10px;
  border-top: 1px solid var(--shelf-soft);
  border-bottom: 1px solid var(--shelf-soft);
}
.rail__scope-line {
  margin-top: 3px;
  font-size: 12px;
  color: var(--ink);
}
.rail__scope-line .tag-num {
  font-size: 14px;
  font-weight: 600;
}
.rail__scope-sub {
  font-size: 10.5px;
  color: var(--ink-faint);
}

.rail__nav {
  flex: 1;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rail__nav-title {
  margin-bottom: 4px;
}

/* 挂钉式导航：像货架挂条上的价签 */
.peg {
  position: relative;
  display: flex;
  gap: 9px;
  align-items: flex-start;
  padding: 7px 8px 7px 9px;
  border: 1px dashed transparent;
  border-left: 2px solid var(--shelf-soft);
  color: var(--ink-soft);
  transition: border-color 160ms var(--ease), background-color 160ms var(--ease),
    transform 160ms var(--ease);
}
.peg:hover {
  text-decoration: none;
  color: var(--ink);
  background: var(--paper-3);
  transform: translateX(2px);
}
.peg.is-active {
  border: 1px dashed var(--tag-deep);
  border-left: 2px solid var(--tag-deep);
  background: var(--tag-pale);
  color: var(--ink);
}
.peg__no {
  font-family: var(--tag-font);
  font-size: 11px;
  font-weight: 600;
  color: var(--tag-deep);
  padding-top: 1px;
}
.peg__body {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.peg__label {
  font-size: 13px;
  font-weight: 500;
}
.peg__hint {
  font-size: 9.5px;
  letter-spacing: 0.04em;
  color: var(--ink-faint);
}

.rail__foot {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--shelf-soft);
}
.rail__user {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
  min-width: 0;
}
.rail__user > div {
  min-width: 0;
}
.rail__user .chip {
  flex: none;
  font-size: 9.5px;
}
.rail__user-name {
  font-size: 12.5px;
  font-weight: 500;
}
.rail__user-mail {
  font-size: 10px;
  color: var(--ink-faint);
  word-break: break-all;
}
.rail__logout {
  margin-top: 8px;
  padding-left: 0;
  font-size: 11px;
}

.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 9px 28px;
  border-bottom: 1px solid var(--shelf-soft);
  background: color-mix(in oklch, var(--paper-2) 70%, var(--paper));
  position: sticky;
  top: 0;
  z-index: 5;
  backdrop-filter: none;
}
.topbar__left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 11px;
}
.topbar__slash {
  color: var(--shelf-soft);
}
.topbar__page {
  font-size: 12px;
  font-weight: 500;
}
.topbar__right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.topbar__meta {
  font-family: var(--tag-font);
  font-size: 9.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
.topbar__dot {
  width: 6px;
  height: 6px;
  background: var(--mint-deep);
  border-radius: 50%;
}
.body {
  padding: 22px 28px 56px;
  flex: 1;
  min-width: 0;
}

@media (max-width: 1279px) {
  .shell {
    grid-template-columns: 208px minmax(0, 1fr);
  }
  .body {
    padding: 20px 20px 48px;
  }
  .rail__scope-sub {
    display: none;
  }
}

@media (max-width: 1023px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .rail {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--shelf);
    padding: 14px 18px 12px;
  }
  .rail__brand {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
  }
  .rail__endcap {
    padding: 6px 10px;
  }
  .rail__endcap-mark {
    font-size: 15px;
  }
  .rail__endcap-sub {
    display: none;
  }
  .rail__wordmark {
    margin-top: 0;
    align-items: flex-end;
  }
  .rail__scope,
  .rail__foot {
    display: none;
  }
  .rail__nav {
    flex-direction: row;
    flex-wrap: wrap;
    margin-top: 10px;
    gap: 6px;
  }
  .rail__nav-title {
    display: none;
  }
  .peg {
    padding: 5px 9px;
    border-left-width: 1px;
  }
  .peg__hint {
    display: none;
  }
  .body {
    padding: 18px 18px 44px;
  }
}

@media (max-width: 767px) {
  .topbar {
    padding: 8px 14px;
  }
  .topbar__right {
    display: none;
  }
  .body {
    padding: 14px 13px 40px;
  }
  .rail {
    padding: 12px 13px 10px;
  }
  .rail__name {
    font-size: 18px;
  }
}
</style>
