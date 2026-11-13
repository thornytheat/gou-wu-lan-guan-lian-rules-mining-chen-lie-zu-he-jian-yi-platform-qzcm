import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/mining' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/ingest',
      name: 'ingest',
      component: () => import('../pages/IngestPage.vue'),
      meta: { title: '补传核对', section: '00 入库', permission: 'baskets:read' },
    },
    {
      path: '/mining',
      name: 'mining',
      component: () => import('../pages/MiningPage.vue'),
      meta: { title: '规则挖掘', section: '01 挖掘' },
    },
    {
      path: '/rules',
      name: 'rules',
      component: () => import('../pages/RulesPage.vue'),
      meta: { title: '规则复核', section: '02 复核' },
    },
    {
      path: '/rules/:id',
      name: 'rule-detail',
      component: () => import('../pages/RuleDetailPage.vue'),
      meta: { title: '规则详情', section: '02 复核' },
    },
    {
      path: '/planogram',
      name: 'planogram',
      component: () => import('../pages/PlanogramPage.vue'),
      meta: { title: '陈列建议', section: '03 陈列' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/mining' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

setupGuards(router)

export default router
