"""演示数据 fixture（离线、确定性；不含任何外部抓取）。

模拟客户：拾光便利 · 品类运营中心（7 人），380 家门店，40 个高频 SKU 参与关联陈列试点。
试点样本：12 家门店 × 7 天（2026-10-05 ~ 10-11）= 3,000 张小票，平均 3.2 行。

40 个 SKU 全部达到 1% 支持度（30 张小票）→ 40 个频繁 1-项集；
预埋 6 组强关联对（每组小票数固定）→ 6 个频繁 2-项集；
没有任何 3-项集达到 1%（所有组合块权重 ≤ 25 < 30）→ 频繁项集合计 46，方向规则 12 条，
通过 lift>1.2 & conf>0.25 过滤后 6 条（每个商品对只保留“小众品 → 大流量品”方向）。

确定性：random.Random(20261112) 的 Mersenne Twister 序列在 CPython 3.11 上稳定；
商品价格经过一次性调参，使 3,000 张小票客单均值精确等于 ¥40.00。
"""
from __future__ import annotations

DEMO_PASSWORD = "Demo@2026"
DEMO_DOMAIN = "basketrule.io"

DEMO_USERS: list[tuple[str, str, str]] = [
    (f"admin@{DEMO_DOMAIN}", "沈亦舟 · 品类总监", "admin"),
    (f"analyst@{DEMO_DOMAIN}", "罗青禾 · 品类运营", "analyst"),
    (f"viewer@{DEMO_DOMAIN}", "临港二店 · 店长（只读）", "viewer"),
]

# 12 家试点门店：4 高客流 / 4 中客流 / 4 低客流
DEMO_STORES: list[dict] = [
    {"code": "S01", "name": "拾光便利·科技园一店", "tier": "high"},
    {"code": "S02", "name": "拾光便利·地铁口店", "tier": "high"},
    {"code": "S03", "name": "拾光便利·大学城店", "tier": "high"},
    {"code": "S04", "name": "拾光便利·万象汇店", "tier": "high"},
    {"code": "S05", "name": "拾光便利·滨江二店", "tier": "mid"},
    {"code": "S06", "name": "拾光便利·老城西店", "tier": "mid"},
    {"code": "S07", "name": "拾光便利·医院店", "tier": "mid"},
    {"code": "S08", "name": "拾光便利·火车站店", "tier": "mid"},
    {"code": "S09", "name": "拾光便利·临港二店", "tier": "low"},
    {"code": "S10", "name": "拾光便利·城北四店", "tier": "low"},
    {"code": "S11", "name": "拾光便利·工业园店", "tier": "low"},
    {"code": "S12", "name": "拾光便利·社区三店", "tier": "low"},
]

# 40 个试点高频 SKU（价格经调参使客单均值 = ¥40.00）
DEMO_SKUS: list[dict] = [
    {"code": "B01", "name": "鲜牛奶 250ml", "category": "乳品", "price": "8.73", "unit": "盒", "shelf_hint": "冷柜第一层"},
    {"code": "B02", "name": "吐司面包 4 片", "category": "烘焙", "price": "12.70", "unit": "袋", "shelf_hint": "H2 烘焙层"},
    {"code": "B03", "name": "原味酸奶 180g", "category": "乳品", "price": "7.14", "unit": "杯", "shelf_hint": "冷柜第二层"},
    {"code": "B04", "name": "金枪鱼饭团", "category": "鲜食", "price": "11.91", "unit": "个", "shelf_hint": "热柜左格"},
    {"code": "B05", "name": "现磨咖啡 中杯", "category": "饮品", "price": "19.05", "unit": "杯", "shelf_hint": "咖啡吧台"},
    {"code": "B06", "name": "无糖豆浆 300ml", "category": "饮品", "price": "5.56", "unit": "瓶", "shelf_hint": "冷柜门侧"},
    {"code": "B07", "name": "卤蛋 单枚", "category": "鲜食", "price": "3.97", "unit": "个", "shelf_hint": "热柜右格"},
    {"code": "B08", "name": "即食麦片 40g", "category": "冲调", "price": "10.80", "unit": "杯", "shelf_hint": "H2 冲调层"},
    {"code": "N01", "name": "精酿啤酒 500ml", "category": "酒类", "price": "15.72", "unit": "罐", "shelf_hint": "端架A 冰饮堆头"},
    {"code": "N02", "name": "盐焗花生 80g", "category": "零食", "price": "7.14", "unit": "袋", "shelf_hint": "H3 坚果层"},
    {"code": "N03", "name": "原味薯片 70g", "category": "零食", "price": "10.32", "unit": "袋", "shelf_hint": "H3 膨化层"},
    {"code": "N04", "name": "小瓶白酒 100ml", "category": "酒类", "price": "23.82", "unit": "瓶", "shelf_hint": "端架A 酒类格"},
    {"code": "N05", "name": "卤味拼盘 150g", "category": "鲜食", "price": "28.58", "unit": "盒", "shelf_hint": "H3 佐餐层"},
    {"code": "N06", "name": "火腿肠 单根", "category": "鲜食", "price": "4.76", "unit": "根", "shelf_hint": "H4 速食层"},
    {"code": "N07", "name": "红烧牛肉面 桶装", "category": "速食", "price": "8.73", "unit": "桶", "shelf_hint": "H4 速食层"},
    {"code": "N08", "name": "可乐 500ml", "category": "饮品", "price": "6.35", "unit": "瓶", "shelf_hint": "冷柜第三层"},
    {"code": "N09", "name": "泡椒凤爪 100g", "category": "零食", "price": "11.91", "unit": "袋", "shelf_hint": "H3 佐餐层"},
    {"code": "N10", "name": "盐水毛豆 120g", "category": "鲜食", "price": "7.94", "unit": "盒", "shelf_hint": "H3 佐餐层"},
    {"code": "D01", "name": "抽取式面巾纸", "category": "日用", "price": "15.72", "unit": "包", "shelf_hint": "H6 日用品层"},
    {"code": "D02", "name": "洗衣液 500ml", "category": "日用", "price": "31.60", "unit": "瓶", "shelf_hint": "H6 日用品层"},
    {"code": "D03", "name": "洗手液 300ml", "category": "日用", "price": "19.85", "unit": "瓶", "shelf_hint": "H6 日用品层"},
    {"code": "D04", "name": "垃圾袋 30 只", "category": "日用", "price": "12.54", "unit": "卷", "shelf_hint": "H7 家居层"},
    {"code": "D05", "name": "薄荷牙膏 90g", "category": "日用", "price": "23.02", "unit": "支", "shelf_hint": "H7 洗护层"},
    {"code": "D06", "name": "洗发水 200ml", "category": "日用", "price": "39.69", "unit": "瓶", "shelf_hint": "H7 洗护层"},
    {"code": "D07", "name": "5 号电池 2 粒", "category": "日用", "price": "15.88", "unit": "板", "shelf_hint": "H7 杂货层"},
    {"code": "D08", "name": "折叠雨伞", "category": "日用", "price": "46.05", "unit": "把", "shelf_hint": "H8 应急层"},
    {"code": "D09", "name": "湿巾 10 抽", "category": "日用", "price": "9.37", "unit": "包", "shelf_hint": "H6 日用品层"},
    {"code": "D10", "name": "一次性拖鞋", "category": "日用", "price": "14.13", "unit": "双", "shelf_hint": "H8 应急层"},
    {"code": "I01", "name": "木糖醇口香糖", "category": "零食", "price": "7.94", "unit": "盒", "shelf_hint": "收银台挂条"},
    {"code": "I02", "name": "黑巧克力 45g", "category": "零食", "price": "13.50", "unit": "块", "shelf_hint": "收银台挂条"},
    {"code": "I03", "name": "棒棒糖 单支", "category": "零食", "price": "3.18", "unit": "支", "shelf_hint": "收银台矮柜"},
    {"code": "I04", "name": "薄荷糖 铁盒", "category": "零食", "price": "5.56", "unit": "盒", "shelf_hint": "收银台矮柜"},
    {"code": "I05", "name": "一次性打火机", "category": "日用", "price": "4.76", "unit": "个", "shelf_hint": "收银台矮柜"},
    {"code": "I06", "name": "冰杯 中号", "category": "冷冻", "price": "3.97", "unit": "个", "shelf_hint": "冷柜门侧"},
    {"code": "I07", "name": "香草冰淇淋", "category": "冷冻", "price": "9.53", "unit": "支", "shelf_hint": "冷柜第三层"},
    {"code": "I08", "name": "矿泉水 550ml", "category": "饮品", "price": "3.18", "unit": "瓶", "shelf_hint": "H1 水饮层"},
    {"code": "C01", "name": "无糖绿茶 500ml", "category": "饮品", "price": "7.94", "unit": "瓶", "shelf_hint": "冷柜第三层"},
    {"code": "C02", "name": "苏打水 480ml", "category": "饮品", "price": "7.14", "unit": "瓶", "shelf_hint": "冷柜第三层"},
    {"code": "C03", "name": "功能饮料 500ml", "category": "饮品", "price": "10.32", "unit": "瓶", "shelf_hint": "H1 水饮层"},
    {"code": "C04", "name": "香烟（硬盒）", "category": "烟草", "price": "34.93", "unit": "盒", "shelf_hint": "收银台背柜"},
]

# 预埋强关联对：cooccur = 该商品对的小票数（固定，决定 ¥ 增量口径）
# trigger_baskets / attach_baskets = 前项 / 后项的全年小票数（由 conf、lift 反推）
PAIR_BUNDLES: list[dict] = [
    {
        "key": "N01>N02", "left": "N01", "right": "N02", "cooccur": 51,
        "trigger_baskets": 202, "attach_baskets": 407, "expected_lift": 1.86,
        "zone": "端架A · 冰饮堆头", "zone_code": "A1",
        "shelf_label": "端架A 上层 · 价签位 01",
        "note": "啤酒与花生同层陈列，端架第一视线高度；三层门店均稳定。",
    },
    {
        "key": "N04>N05", "left": "N04", "right": "N05", "cooccur": 44,
        "trigger_baskets": 168, "attach_baskets": 410, "expected_lift": 1.92,
        "zone": "端架A · 冰饮堆头", "zone_code": "A1",
        "shelf_label": "端架A 上层 · 价签位 02",
        "note": "白酒与卤味同端架；与啤酒组合争用同一端架位，属冲突组。",
    },
    {
        "key": "N07>N06", "left": "N07", "right": "N06", "cooccur": 41,
        "trigger_baskets": 155, "attach_baskets": 405, "expected_lift": 1.96,
        "zone": "H4 速食层", "zone_code": "H4",
        "shelf_label": "H4 速食层 · 眼高位",
        "note": "泡面旁加火腿肠挂条，夜间时段重点补货。",
    },
    {
        "key": "B03>B02", "left": "B03", "right": "B02", "cooccur": 37,
        "trigger_baskets": 138, "attach_baskets": 400, "expected_lift": 2.01,
        "zone": "冷柜B · 早餐角", "zone_code": "B2",
        "shelf_label": "冷柜B 第二层 · 早餐角",
        "note": "酸奶与吐司组成 9.9 元早餐组合。",
    },
    {
        "key": "B05>B04", "left": "B05", "right": "B04", "cooccur": 35,
        "trigger_baskets": 134, "attach_baskets": 400, "expected_lift": 1.96,
        "zone": "H1 热柜旁", "zone_code": "H1",
        "shelf_label": "H1 热柜旁 · 咖啡加购位",
        "note": "咖啡吧台加饭团立牌，工作日早高峰转化最好。",
    },
    {
        "key": "N08>N03", "left": "N08", "right": "N03", "cooccur": 44,
        "trigger_baskets": 166, "attach_baskets": 402, "expected_lift": 1.98,
        "zone": "H3 零食层", "zone_code": "H3",
        "shelf_label": "H3 膨化层 · 端头位",
        "note": "可乐与薯片组合陈列，学生客群转化高。",
    },
]

# 其余 28 个 SKU 的相对权重（生成器按总量缩放，保证支持度 2%~8%）
FILLER_WEIGHTS: dict[str, int] = {
    "B01": 240, "B06": 168, "B07": 196, "B08": 148,
    "N09": 208, "N10": 172,
    "D01": 232, "D02": 132, "D03": 148, "D04": 184,
    "D05": 120, "D06": 96, "D07": 136, "D08": 72,
    "D09": 200, "D10": 88,
    "I01": 224, "I02": 168, "I03": 188, "I04": 160,
    "I05": 212, "I06": 156, "I07": 176, "I08": 248,
    "C01": 216, "C02": 164, "C03": 180, "C04": 112,
}

SAMPLE_START = "2026-10-05"
SAMPLE_DAYS = 7
BASKET_TOTAL = 3000
SINGLE_BASKETS = 600
PAIR_BASKET_TOTAL = sum(spec["cooccur"] for spec in PAIR_BUNDLES)
# 组合块规模分布（3/4/5 行），合计 3000 - 252 - 600 = 2148 张、8496 行
COMBO_SIZE_BUCKETS: list[tuple[int, int]] = [(3, 200), (4, 1844), (5, 104)]
TEMPLATE_WEIGHT = 25

CHANNELS = ["pos", "pos", "pos", "self_checkout", "mini_program"]
# 剩余小票（不含预埋对与关联主商品小票）的行数分布：4 行 / 5 行
FILLER_BLOCK_LINES = (4, 5)

PLAN_CODE_SEED = "PLAN-2026-W44"
SEED_RUN_LABEL = "RUN-2026-W41-DEMO"


def sku_price_map() -> dict[str, float]:
    return {item["code"]: float(item["price"]) for item in DEMO_SKUS}


def sku_name_map() -> dict[str, str]:
    return {item["code"]: item["name"] for item in DEMO_SKUS}


def rule_meta_by_key() -> dict[str, dict]:
    return {spec["key"]: spec for spec in PAIR_BUNDLES}
