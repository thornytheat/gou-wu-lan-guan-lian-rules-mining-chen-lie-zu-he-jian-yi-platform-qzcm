"""运行时限额（可从环境变量覆盖）。"""
from __future__ import annotations

from src.config.settings import settings

RATE_LIMIT_MINING_PER_MINUTE = settings.rate_limit_mining_per_minute
RATE_LIMIT_INGEST_PER_MINUTE = settings.rate_limit_ingest_per_minute
RATE_LIMIT_DEFAULT_PER_MINUTE = settings.rate_limit_default_per_minute

# 列表分页上限，避免一次拉全量频繁项集
MAX_PAGE_SIZE = 200
MAX_ITEMSET_PAGE = 500
# 单次挖掘最多扫描小票数（demo 数据 3,000；上限保护）
MAX_BASKETS_PER_RUN = 20000
# 反例样本保留条数
MAX_COUNTEREXAMPLES = 5
