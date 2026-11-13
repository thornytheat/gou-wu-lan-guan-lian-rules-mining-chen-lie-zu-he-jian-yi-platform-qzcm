"""测试包根配置：保证 `import src.*` 在容器内（WORKDIR=/app）与宿主都能解析。

约定：单测只 import 纯函数模块（apriori_service / stability_service / *_core / utils.stats /
fixtures_loader），不建立数据库连接、不读 Redis、不 mock 算法。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
