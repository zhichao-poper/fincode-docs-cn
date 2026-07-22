#!/usr/bin/env python3
"""检查 fincode 官方 OpenAPI 是否发生变化，不自动覆盖人工翻译基线。"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "fincode-openapi.ja.yml"
URL = "https://docs.fincode.jp/assets/api/fincode-openapi.yml"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    request = urllib.request.Request(URL, headers={"User-Agent": "fincode-docs-cn-upstream-check/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        remote = response.read()
    local = SOURCE.read_bytes()
    local_hash = sha256(local)
    remote_hash = sha256(remote)
    if local_hash != remote_hash:
        print(f"上游 OpenAPI 已变化：local={local_hash} remote={remote_hash}")
        print("请先审阅差异，再更新 source 快照并补充人工译文。")
        sys.exit(1)
    print(f"上游 OpenAPI 未变化：sha256={local_hash}")


if __name__ == "__main__":
    main()

