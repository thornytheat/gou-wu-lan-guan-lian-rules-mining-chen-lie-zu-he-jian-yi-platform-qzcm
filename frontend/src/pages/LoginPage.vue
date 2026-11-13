<template>
  <div class="login">
    <section class="stage">
      <div class="stage__top">
        <div class="stage__endcap">
          <span class="stage__endcap-mark">拾光便利</span>
          <span class="stage__endcap-sub">品类运营中心 · 关联陈列试点</span>
        </div>
        <div class="stage__wordmark">
          <span class="stage__brand">basketrule</span>
          <span class="eyebrow">basket · affinity · planogram</span>
        </div>
      </div>

      <h1 class="stage__title">
        先看篮子，<br />再摆货架。
      </h1>
      <p class="stage__desc">
        把 POS 小票变成可执行的陈列动作：频繁项集 → 关联规则 → 门店分层稳定性 → 货架位与增量估算，
        每一步都在后端真算，工单可导出给店长执行。
      </p>

      <figure class="stage__shelf" aria-hidden="true">
        <svg viewBox="0 0 520 262">
          <g class="shelf-line">
            <line x1="0" y1="74" x2="520" y2="74" />
            <line x1="0" y1="168" x2="520" y2="168" />
            <line x1="0" y1="250" x2="520" y2="250" />
          </g>
          <g class="goods">
            <rect x="16" y="22" width="30" height="52" rx="2" />
            <rect x="52" y="30" width="24" height="44" rx="2" />
            <rect x="82" y="16" width="38" height="58" rx="2" />
            <rect x="126" y="34" width="22" height="40" rx="2" />
            <rect x="200" y="24" width="34" height="50" rx="2" />
            <rect x="240" y="14" width="26" height="60" rx="2" />
            <rect x="272" y="28" width="42" height="46" rx="2" />
            <rect x="322" y="20" width="24" height="54" rx="2" />
            <rect x="404" y="26" width="36" height="48" rx="2" />
            <rect x="446" y="16" width="26" height="58" rx="2" />
            <rect x="478" y="32" width="24" height="42" rx="2" />

            <rect x="18" y="112" width="42" height="56" rx="2" />
            <rect x="66" y="120" width="26" height="48" rx="2" />
            <rect x="98" y="104" width="34" height="64" rx="2" />
            <rect x="170" y="116" width="30" height="52" rx="2" />
            <rect x="206" y="108" width="44" height="60" rx="2" />
            <rect x="256" y="122" width="24" height="46" rx="2" />
            <rect x="320" y="110" width="38" height="58" rx="2" />
            <rect x="364" y="120" width="26" height="48" rx="2" />
            <rect x="432" y="114" width="32" height="54" rx="2" />
            <rect x="470" y="106" width="28" height="62" rx="2" />

            <rect x="22" y="200" width="50" height="50" rx="2" />
            <rect x="80" y="208" width="28" height="42" rx="2" />
            <rect x="114" y="196" width="40" height="54" rx="2" />
            <rect x="188" y="206" width="26" height="44" rx="2" />
            <rect x="220" y="198" width="44" height="52" rx="2" />
            <rect x="270" y="210" width="24" height="40" rx="2" />
            <rect x="334" y="202" width="36" height="48" rx="2" />
            <rect x="376" y="208" width="26" height="42" rx="2" />
            <rect x="444" y="200" width="34" height="50" rx="2" />
            <rect x="484" y="206" width="22" height="44" rx="2" />
          </g>
          <g class="hang">
            <line x1="140" y1="74" x2="140" y2="92" />
            <rect x="108" y="92" width="64" height="30" />
            <text x="116" y="105">啤酒+花生</text>
            <text x="116" y="117" class="hang__num">lift 1.86</text>

            <line x1="296" y1="168" x2="296" y2="186" />
            <rect x="258" y="186" width="76" height="30" />
            <text x="266" y="199">可乐+薯片</text>
            <text x="266" y="211" class="hang__num">¥2,640</text>

            <line x1="418" y1="250" x2="418" y2="236" />
            <rect x="382" y="206" width="72" height="30" />
            <text x="390" y="219">端架A · 冰饮</text>
            <text x="390" y="231" class="hang__num">5 / 6 位</text>
          </g>
        </svg>
        <figcaption>
          40 个高频 SKU · 12 家试点门店 · 3,000 张小票 / 7 天 · 平均 3.2 行
        </figcaption>
      </figure>

      <div class="stage__stats">
        <div class="stage__stat">
          <span class="tag-num">46</span>
          <span>频繁项集</span>
        </div>
        <div class="stage__stat">
          <span class="tag-num">6</span>
          <span>通过过滤的规则</span>
        </div>
        <div class="stage__stat">
          <span class="tag-num">¥12,480</span>
          <span>五席货架位预估月增量</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel__box">
        <div class="panel__head">
          <span class="eyebrow">sign in</span>
          <h2>登录品类运营台</h2>
          <p>用演示账号进入；三种角色的可操作范围不同。</p>
        </div>

        <form class="panel__form" @submit.prevent="submit">
          <label class="panel__field">
            <span class="label">邮箱</span>
            <input
              v-model="email"
              class="field"
              type="email"
              autocomplete="username"
              placeholder="admin@basketrule.io"
              data-test="email"
            />
          </label>
          <label class="panel__field">
            <span class="label">密码</span>
            <input
              v-model="password"
              class="field"
              type="password"
              autocomplete="current-password"
              placeholder="Demo@2026"
              data-test="password"
            />
          </label>

          <div v-if="error" class="panel__error">{{ error }}</div>

          <button class="btn btn--mint panel__submit" type="submit" :disabled="auth.loading" data-test="submit">
            {{ auth.loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <div class="panel__demo">
          <div class="label">演示账号（密码均为 Demo@2026）</div>
          <button
            v-for="account in accounts"
            :key="account.email"
            type="button"
            class="demo-card"
            @click="fill(account.email)"
          >
            <span class="demo-card__role">{{ account.role }}</span>
            <span class="demo-card__mail">{{ account.email }}</span>
            <span class="demo-card__scope">{{ account.scope }}</span>
          </button>
        </div>

        <div class="panel__foot">
          <span>拾光便利 · 品类运营中心（7 人）</span>
          <span class="panel__foot-dim">380 家门店 / 40 SKU 试点</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('admin@basketrule.io')
const password = ref('Demo@2026')
const error = ref('')

const accounts = [
  { email: 'admin@basketrule.io', role: '品类总监', scope: '参数 / 审核 / 发布 / 导出' },
  { email: 'analyst@basketrule.io', role: '品类运营', scope: '跑挖掘 / 筛规则 / 提建议' },
  { email: 'viewer@basketrule.io', role: '店长', scope: '只读已发布陈列建议' },
]

function fill(value: string) {
  email.value = value
  password.value = 'Demo@2026'
  error.value = ''
}

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = (route.query.redirect as string) || '/mining'
    router.push(redirect)
  } catch (err) {
    error.value = (err as Error).message ?? '登录失败'
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
}

.stage {
  padding: 34px 44px 36px;
  border-right: 1px solid var(--shelf);
  background: var(--paper-2);
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
}
.stage__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}
.stage__endcap {
  background: var(--mint);
  border: 1px solid var(--mint-deep);
  padding: 8px 12px 7px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 -3px 0 oklch(50% 0.08 168 / 0.22);
}
.stage__endcap-mark {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--mint-ink);
}
.stage__endcap-sub {
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: var(--mint-ink);
  opacity: 0.85;
}
.stage__wordmark {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.stage__brand {
  font-family: var(--tag-font);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1;
}
.stage__title {
  font-size: clamp(28px, 3.4vw, 44px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-top: 8px;
}
.stage__desc {
  font-size: 13px;
  color: var(--ink-soft);
  max-width: 56ch;
}
.stage__shelf {
  margin: 6px 0 0;
  border-top: var(--shelf-line);
  padding-top: 10px;
}
.stage__shelf svg {
  width: 100%;
  height: auto;
  display: block;
}
.shelf-line line {
  stroke: var(--shelf);
  stroke-width: 2.5;
}
.goods rect {
  fill: var(--paper-3);
  stroke: var(--shelf-soft);
}
.goods rect:nth-child(3n) {
  fill: var(--mint-pale);
  stroke: var(--mint);
}
.goods rect:nth-child(4n) {
  fill: var(--tag-pale);
  stroke: var(--tag-deep);
}
.hang line {
  stroke: var(--shelf-dark);
  stroke-width: 1;
}
.hang rect {
  fill: var(--tag);
  stroke: var(--tag-deep);
}
.hang text {
  font-size: 8px;
  fill: oklch(38% 0.04 80);
  font-family: var(--sans);
}
.hang .hang__num {
  font-family: var(--tag-font);
  font-size: 8.5px;
  font-weight: 600;
}
.stage__shelf figcaption {
  margin-top: 6px;
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--ink-faint);
}
.stage__stats {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
  border-top: 1px solid var(--shelf-soft);
  padding-top: 12px;
  margin-top: auto;
}
.stage__stat {
  display: flex;
  flex-direction: column;
}
.stage__stat .tag-num {
  font-size: 20px;
  font-weight: 600;
}
.stage__stat span:last-child {
  font-size: 10px;
  color: var(--ink-faint);
}

.panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 34px 40px;
  background: var(--paper);
}
.panel__box {
  width: 100%;
  max-width: 392px;
}
.panel__head h2 {
  margin-top: 3px;
  font-size: 21px;
  font-weight: 700;
}
.panel__head p {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-soft);
}
.panel__form {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.panel__error {
  border: 1px solid var(--alert);
  background: var(--alert-pale);
  color: var(--alert);
  font-size: 12px;
  padding: 7px 10px;
}
.panel__submit {
  margin-top: 4px;
  width: 100%;
  padding: 10px;
}
.panel__demo {
  margin-top: 22px;
  border-top: 1px solid var(--shelf-soft);
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.demo-card {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  grid-template-rows: auto auto;
  gap: 0 8px;
  text-align: left;
  background: var(--paper-2);
  border: 1px dashed var(--shelf);
  padding: 7px 10px;
  cursor: pointer;
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease);
}
.demo-card:hover {
  background: var(--tag-pale);
  border-color: var(--tag-deep);
}
.demo-card__role {
  grid-row: span 2;
  align-self: center;
  font-size: 11px;
  color: var(--mint-ink);
  border-left: 2px solid var(--mint-deep);
  padding-left: 7px;
}
.demo-card__mail {
  font-family: var(--tag-font);
  font-size: 11.5px;
  word-break: break-all;
}
.demo-card__scope {
  font-size: 10px;
  color: var(--ink-faint);
}
.panel__foot {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 10px;
  color: var(--ink-faint);
  border-top: 1px solid var(--shelf-soft);
  padding-top: 10px;
}
.panel__foot-dim {
  text-align: right;
}

@media (max-width: 1023px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }
  .stage {
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid var(--shelf);
    padding: 22px 24px 20px;
    gap: 12px;
  }
  .stage__shelf {
    display: none;
  }
  .stage__stats {
    margin-top: 4px;
  }
  .panel {
    padding: 24px;
  }
  .panel__box {
    max-width: 520px;
  }
}

@media (max-width: 767px) {
  .stage {
    padding: 16px 15px 14px;
  }
  .stage__top {
    flex-direction: column;
    gap: 10px;
  }
  .stage__wordmark {
    align-items: flex-start;
  }
  .stage__title {
    font-size: 27px;
  }
  .stage__stats {
    gap: 14px;
  }
  .panel {
    padding: 18px 15px 32px;
  }
}
</style>
