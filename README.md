# basketrule · 购物篮关联规则挖掘与陈列组合建议台

> 一句话：把 3,000 张便利店小票算成「哪两个商品该摆在一起、摆在哪个货架位、一个月能多卖多少钱」，
> 并把结论变成店长可直接执行的陈列工单。

模拟客户：**拾光便利 · 品类运营中心**（7 人），380 家门店，40 个高频 SKU 参与关联陈列试点。
试点样本：12 家门店 × 7 天（2026-10-05 ~ 10-11）= **3,000 张小票 / 9,600 行**，平均 3.2 行，客单均值 ¥40.00。

## 1. 真实场景

| | 内容 |
|---|---|
| 现有工作流 | 店长凭经验把啤酒和花生摆一起；季度复盘时运营从 POS 导出小票到 Excel，人工数「谁和谁一起买」，样本一多就放弃 |
| 痛点 ① | 关联强度没有量化口径（只有「感觉卖得好」） |
| 痛点 ② | 规则一跑几百条，无法筛出可执行项 |
| 痛点 ③ | 陈列位有限，采纳哪几条没有收益估算与稳定性校验 |
| 上游 | POS 小票与商品主数据（本仓库内置离线 fixture，确定性可复现） |
| 本系统替代 | 「Excel 手数 + 店长经验」这一段：频繁项集 → 规则过滤 → 门店分层稳定性 → 货架位贪心选择 → 工单 |
| 下游 | 陈列调整工单（CSV）→ 店长执行 → 一周后回看连带率 |

**一天的工作剧本**（也是演示顺序）

0. 08:50 店长把前一天的补传文件交给运营；罗青禾在「补传核对」导入，看到 **接收 1 / 重复 1 / 作废 2 / 更正 1 / 拒绝 2**：
   重复内容不新增、作废小票不参与挖掘、更正生成新版本并取代旧版本、未知 SKU 与负数量被拒。
1. 09:05 品类运营罗青禾登录，打开「规则挖掘」，确认样本：3,000 张小票 / 40 SKU / 客单 ¥40.00。
2. 09:08 用默认参数（min_support 0.01、max_itemset 3）点「运行挖掘」，2 秒内出结果：**46 个频繁项集**。
3. 09:10 过滤（lift > 1.2 且 conf > 0.25）后剩 **6 条规则**；`啤酒 → 花生` lift **1.86**，Wilson 95% 区间 `[1.42, 2.44]`。
4. 09:14 打开规则详情，看三层门店 lift（1.80 / 1.83 / 1.97，CI 下界均 > 1）→ 判定「三层稳定」；再看反例小票 151 张。
5. 09:20 生成陈列建议：K=6 贪心背包，`白酒 → 卤味` 与 `啤酒 → 花生` 争用端架 A，剔除增量更低的一条 → **5 个货架位**。
6. 09:25 预估月增量 **¥12,480**（5 席合计，口径见 §4）。
7. 09:28 品类总监沈亦舟复核，批量采纳 **3 条**（啤酒→花生、方便面→香肠、可乐→薯片）。
8. 09:32 发布建议单，店长端（viewer）立即可见，但不能改参数 / 复核 / 导出。
9. 09:35 导出工单 CSV：表头 + **3 行**（只含已采纳规则）。
10. 09:40 审计日志记录登录、跑挖掘、复核、发布、导出五类动作，含 trace_id。

## 2. 功能（5 个业务模块串成链路）

0. **补传核对**（`/ingest`）：每日补传入库。按 (发生时间, 来源序号, 到达序号) 确定每张小票的**唯一有效内容**；
   同一批里逐票处置为 接收 / 重复 / 作废 / 更正 / 拒绝 五类计数；可回放任意批次的逐票台账，并查看全部最终有效小票（含版本号）。
   已发布建议单绑定生成时的批次与版本口径，晚到的作废 / 更正只影响之后的新分析。
1. **参数与挖掘**（`/mining`）：小票样本概览、Apriori 参数（min_support / 规则置信度下限 / max_itemset / 过滤阈值）、
   运行批次、频繁项集分页、最近批次、小票样本。批次异步派发到 Celery worker，前端轮询状态。
2. **规则复核**（`/rules`）：关键词 / 状态 / 稳定性 / lift 下限筛选，按增量或 lift 排序，批量采纳，规则 CSV 导出。
3. **稳定性与归因**（`/rules/:id`）：共现矩阵热力图（SVG 自绘）、三层门店 lift + Wilson 区间、反例小票、增量口径拆解、
   复核记录（采纳 / 挂起 / 驳回，理由必填写入审计）。
4. **陈列建议与工单**（`/planogram`）：货架位可视化、冲突组消解说明、预估月增量、发布、工单 CSV 导出、建议单历史。

横切：JWT + 三角色 RBAC（低权角色调高权接口真实 403）、审计日志、Redis 滑动窗口限流、统一错误收敛。

### 补传口径（可核对的入库过程）

| 情形 | 处置 | 对小票版本的影响 |
|---|---|---|
| 首次补传 | 接收 | 新增 version=1 的 `active` 行 |
| 同票同内容（重复补传） | 重复 | 不新增行；「重复补传不新增」 |
| 同票不同内容、但没声明更正 | 拒绝 | 不改动任何状态：旧内容不能被直接覆盖 |
| 作废（先到 / 后到） | 作废 | 该票没有有效版本；作废后才到的原票也不生效 |
| 更正（`same_as_no` 指向目标票） | 更正 | 生成 version+1 的 `active` 行，旧版本转 `superseded`（历史保留） |
| 未知 SKU / 数量非正 / 金额为负 / 缺发生时间 | 拒绝 | 不改动任何状态 |

- 发生顺序优先于上传先后：晚到的旧发生时间记录排在前面，不会偷改历史。
- 挖掘、概览、反例、SKU 支持度只读 `status=active` 的版本；`superseded` / `voided` 不参与任何计数。
- 每批导入写一条 `basket_ingest_records` 台账（`detail` 是逐票处置结果、`event_seq` 是处置序号）并落审计日志 `basket.import`。

## 3. 快速启动

```bash
cd gb-586
cp .env.example .env          # 端口 / 库名 / JWT 全在 .env
docker compose up -d --build  # 5 个服务：frontend / backend / worker / db / redis
docker compose ps             # 等 5/5 healthy（首次约 60-90s）
```

- 前端：<http://localhost:18259>
- 后端 OpenAPI：<http://localhost:19259/api/docs>（直连；前端统一走 Nginx 的 `/api/` 反代）
- 数据库：`localhost:17759`（PostgreSQL 16，schema `basketrule`）

`SEED_DEMO=true` 时 backend 启动会自动执行一次幂等 seed（3,000 张小票 + 1 个演示挖掘批次 + 1 个已发布样板位 + 3 个账号），
也可手动重跑：

```bash
docker compose exec backend python -m scripts.seed_demo
# 末尾固定输出：
# SEED_SUMMARY brand=basketrule skus=40 baskets=3000 rules=6 slots=1 users=3
```

本地开发：

```bash
# 后端（需本机 PG + Redis）
cd backend && pip install -r requirements.txt && uvicorn src.main:app --reload --port 19259
# 前端
cd frontend && npm install && npm run dev   # http://localhost:18259，/api 代理到 19259
```

## 4. 演示账号（密码统一 `Demo@2026`）

| 邮箱 | 角色 | 权限 | 典型动作 |
|---|---|---|---|
| `admin@basketrule.io` | 品类总监 admin | `mining:run` `rules:review` `rules:publish` `planogram:write` `planogram:publish` `rules:export` `baskets:read` `audit:read` | 参数、审核、发布、导出 |
| `analyst@basketrule.io` | 品类运营 analyst | `mining:run` `rules:review` `planogram:write` `rules:export` `baskets:read` | 跑挖掘、筛规则、提建议 |
| `viewer@basketrule.io` | 店长 viewer | `mining:read` `rules:read` `planogram:read` | 只看已发布陈列建议 |

真实 403 示例（不是前端隐藏按钮）：

```bash
# 店长读取补传台账 → 403
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $VIEWER_TOKEN" \
  http://localhost:18259/api/ingest/summary
# 店长提交补传批次 → 403
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"batch_no":"ING-X","records":[]}' \
  http://localhost:18259/api/ingest/import
# 店长导出工单 → 403
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $VIEWER_TOKEN" \
  http://localhost:18259/api/planogram/PLAN-2026-W45/export
# 店长跑挖掘 → 403
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"min_support":0.01}' \
  http://localhost:18259/api/mining/runs
# 店长读小票明细 → 403
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $VIEWER_TOKEN" \
  http://localhost:18259/api/baskets/summary
```

## 5. 算法口径（后端 Python 真算，前端只展示）

### 算法 0：补传版本折算（`backend/src/services/ingest_core.py`，纯函数）

- 排序键 `(occurred_at, source_seq, arrive_seq)`；版本链按票号归并。
- 内容指纹 = `sha256(basket_no + 按 SKU 升序的 (sku, qty))`：金额尾差与明细行顺序不制造重复版本；内容变化必须走更正。
- 不变量（`backend/tests/test_ingest.py` + `test_invariants.py`）：五类计数之和 = 记录条数；
  重复不新增版本；作废后 `final_baskets` 不含该票；更正后最终版本一定是链尾；拒绝不改变任何已有状态。
- demo 批次：接收 1 · 重复 1 · 作废 2 · 更正 1 · 拒绝 2（作废命中 1 张有效小票，另 1 条是「作废先到」的占位）。

### 算法 1：Apriori 频繁项集与关联规则（`backend/src/services/apriori_service.py`）

- 逐层候选生成 + 支持度计数 + 剪枝；参数 `min_support=0.01`（3,000 × 1% = 30 张）、`max_itemset=3`。
- 指标：`support(A∪B)`、`confidence = sup(A∪B)/sup(A)`、`lift = confidence/sup(B)`、
  `conviction = (1−sup(B))/(1−confidence)`。
- 候选规则按置信度下限（默认 0.05）留出方向规则；业务过滤 `lift > 1.2 且 confidence > 0.25`。
- demo 实测：**46 个频繁项集**（40 个单品 + 6 个商品对，无三项集达标）→ **12 条候选规则**（6 个商品对 × 2 个方向）→ **6 条通过过滤**
  （6 个商品对各保留「小众品 → 大流量品」一个方向，反向置信度 < 0.25 被过滤）。

### 算法 2：门店分层稳定性 + 增量 + 陈列选择（`stability_service.py` / `planogram_service.py`）

- 高 / 中 / 低客流各 1,000 张小票；每层算 lift，并对共现小票比例做 **Wilson 95% 区间**，再折算为 lift 区间。
- 稳定 = 三层 lift 均 > 1.15 且三层 CI 下界均 > 1。
- 预估月增量 = 共现小票数 × 客单均值 × 采纳率 0.35 × (30 / 样本天数 7)。
- K=6 贪心背包：按增量排序，同冲突组（同一货架分区）只取一条。
- demo 实测：`啤酒 → 花生` lift **1.86**、CI `[1.42, 2.44]`、三层 lift 1.80/1.83/1.97 → 稳定；
  6 条规则里 `白酒 → 卤味` 与 `啤酒 → 花生` 同属端架 A → 剔除 1 条 → **5 个货架位、合计月增量 ¥12,480**
  （51+41+37+35+44 = 208 张共现 × ¥40.00 × 0.35 × 30/7）。

**可复现**：seed 用固定 `random.Random(20261112)` 生成小票，价格经过一次性调参使客单均值精确为 ¥40.00；
两次 seed 输出同一行 `SEED_SUMMARY`。seed 基线小票直接落为 `version=1 / active / source_batch=SEED-BASELINE`，
不经过补传链路，因此导入页的批次台账从 0 开始。

**版本口径**：建议单快照 `basket_basis`（来源批次、参与挖掘的有效小票数、生成后新入库的批次数）随建议单返回；
工单 CSV 也带「小票版本口径」列。已发布建议单不会被之后到达的作废 / 更正回写。

## 6. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite 5 + Pinia + Vue Router + Axios；图表为 SVG 自绘（无图表库 / 无 CDN） |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2 |
| 异步 | Celery 5.4 + Redis 7（worker 消费挖掘任务 + beat 心跳） |
| 数据库 | PostgreSQL 16（schema `basketrule`，JSONB 存小票明细与项集快照） |
| 网关 | Nginx 1.27（托管 dist + `/api/` 反代 + SPA 回落） |
| 鉴权 | JWT（PyJWT）+ bcrypt + 三角色能力矩阵 |

## 7. 目录

```
gb-586/
├── docker-compose.yml
├── .env / .env.example
├── backend/
│   ├── Dockerfile / entrypoint.sh / requirements.txt / alembic.ini
│   ├── migrations/                 # alembic 初始迁移（容器内实际走 create_all）
│   ├── scripts/                    # bootstrap_db / fixtures / fixtures_baskets / seed_demo
│   └── src/
│       ├── config/                 # settings / database / app / celery_app
│       ├── constants/              # enums（共享枚举）/ roles / error_codes / limits / log_templates
│       ├── models/                 # user / sku / order_basket(版本化) / basket_ingest_record / mining_run / rule_candidate / rule_review / planogram_slot / audit_log
│       ├── schemas/                # auth / basket / mining / rule / planogram
│       ├── services/               # ingest_core / ingest / apriori / stability / planogram / mining / rule / basket / export / audit / auth
│       ├── controllers/ routes/    # 8 组路由，统一 /api 前缀（含 /ingest）
│       ├── middlewares/            # auth / rbac / audit_logger / error_handler / rate_limit
│       └── utils/                  # jwt / password / stats(Wilson) / redis / errors / logger
├── worker/
│   ├── Dockerfile / healthcheck.sh
│   └── src/{config,core,tasks}      # celery app / redis 心跳 / 挖掘任务 + beat
└── frontend/
    ├── Dockerfile / nginx.conf / vite.config.ts
    └── src/{api,stores,types,components/common,hooks,pages,router,utils,constants,styles}
```

## 8. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `basketrule` | 容器名前缀 |
| `FRONTEND_PORT` | `18259` | 前端宿主端口（映射容器 80） |
| `BACKEND_PORT` | `19259` | 后端宿主端口（映射容器 8000） |
| `DB_PORT` | `17759` | PostgreSQL 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `basketrule` / `basketrule` / `basketrule_pw_2026` | 数据库 |
| `JWT_SECRET` | dev 值 | JWT 签名密钥（生产必改） |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker / 限流 / 心跳 |
| `SEED_DEMO` | `true` | 启动时执行一次幂等 seed |
| `RATE_LIMIT_MINING_PER_MINUTE` | `6` | 每用户每分钟最多跑几次挖掘 |
| `RATE_LIMIT_INGEST_PER_MINUTE` | `12` | 每用户每分钟最多提交几次补传 |

## 9. Docker 说明

- 恰好 5 个服务，全部带 healthcheck：`frontend`（wget `/healthz`）、`backend`（curl `/api/health`，含 DB ping）、
  `worker`（Redis 心跳 + `celery inspect ping` 兜底）、`db`（`pg_isready`）、`redis`（`redis-cli ping`）。
- `depends_on` 用 `service_healthy`（frontend 依赖 backend healthy；backend/worker 依赖 db + redis healthy）。
- 命名卷：`db_data`（PG 数据）、`redis_data`（AOF）。
- 构建参数：前端 `NPM_REGISTRY` 默认 `https://registry.npmmirror.com`；后端 pip 走清华源。
- 源码目录不含任何截图 / 日志 / 测试脚本；测试产物统一在 `test-artifacts/gb-586/`。

## 10. 共享枚举出现位置

**枚举组 1：门店分层 / 批次状态 / 规则状态 / 复核动作 / 建议位状态 / 小票渠道**

| 位置 | 作用 |
|---|---|
| `backend/src/constants/enums.py` | 定义 `StoreTier` `RunStatus` `RuleStatus` `ReviewDecision` `SlotStatus` `Channel` + 中文标签 |
| `backend/src/models/*.py` | 列默认值（`status` 默认 `queued` / `candidate` / `draft`） |
| `backend/src/schemas/*.py` | `ReviewRequest.decision`、`SlotUpdateRequest.status` 的 Literal 校验 |
| `backend/src/services/{mining,rule,planogram,export}_service.py` | 状态流转与标签映射 |
| `backend/src/constants/roles.py` | 角色与能力矩阵 |
| `frontend/src/constants/enums.ts` | 镜像定义 + 中文标签 |
| `frontend/src/constants/roles.ts` | 角色镜像 + 角色任务说明 |
| `frontend/src/types/domain.ts` | 联合类型（`RunStatus` / `RuleStatus` / …） |
| `frontend/src/pages/*.vue`、`components/common/*.vue` | 标签渲染与状态 chip |

**枚举组 3：补传记录类型（supplement / void / correction）与处置结果（received / duplicate / voided / corrected / rejected）**

| 位置 | 作用 |
|---|---|
| `backend/src/constants/ingest.py` | 定义 `IngestRecordType` `IngestResult` + 中文标签 + 五类计数顺序 |
| `backend/src/services/ingest_core.py` | 版本折算状态机与逐票台账行 |
| `backend/src/models/order_basket.py` | 版本状态 `active` / `superseded` / `voided` |
| `backend/src/schemas/ingest.py` | `IngestRecordIn.record_type` 的 Literal 校验 |
| `frontend/src/constants/ingest.ts` | 镜像定义 + 标签 + chip 配色 |
| `frontend/src/types/domain.ts` | 联合类型（`IngestRecordType` / `IngestResult`） |
| `frontend/src/pages/IngestPage.vue` | 五类计数、逐票台账、最终有效小票 |

**枚举组 2：角色（admin / analyst / viewer）与能力（mining:run / rules:review / rules:publish / planogram:write / planogram:publish / rules:export / audit:read / baskets:read / baskets:import）**

| 位置 | 作用 |
|---|---|
| `backend/src/constants/roles.py` | `PERMISSIONS` 能力矩阵 + 角色标签 |
| `backend/src/middlewares/rbac.py` | `require_permission(action)` 真实 403 |
| `backend/src/services/auth_service.py` | 登录响应携带 `permissions[]` |
| `backend/src/routes/*.py` | 每个路由声明所需 action |
| `frontend/src/constants/roles.ts` | 角色标签 / 任务描述 |
| `frontend/src/stores/authStore.ts` | `can(action)` 控制按钮可用性（仅体验层，真拦在后端） |
| `frontend/src/pages/{Mining,Rules,RuleDetail,Planogram}Page.vue` | 按钮禁用 + 只读提示 |

## 11. 已知取舍

见 `test-artifacts/gb-586/TESTING.md`「已知差异」：候选规则条数与计划书的差异、Google Fonts 离线回退、
seed 占位建议单只有 1 个位、工单 CSV 只导出已采纳规则等。

## License

MIT
