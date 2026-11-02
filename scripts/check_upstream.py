#!/usr/bin/env python3
"""检查 fincode 官方 OpenAPI 是否发生变化，不自动覆盖人工翻译基线。

上游有变化时，同时列出原文新增、修改、删除的文本位置（JSON Pointer）。
译文按位置或字段名对应原文，原文改了而译文没改时生成与校验都不会报错，
所以更新快照时必须逐条核对这里列出的位置对应的中文。
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "fincode-openapi.ja.yml"
URL = "https://docs.fincode.jp/assets/api/fincode-openapi.yml"
TRANSLATABLE_KEYS = {"title", "summary", "description"}
PREVIEW_LENGTH = 80


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_pointer_part(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def collect_texts(value: Any, pointer: str = "", result: dict[str, str] | None = None) -> dict[str, str]:
    """收集所有需要翻译的文本，键为 JSON Pointer。"""
    if result is None:
        result = {}
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{pointer}/{encode_pointer_part(str(key))}"
            if isinstance(item, str) and (key in TRANSLATABLE_KEYS or str(key).startswith("x-description-")):
                result[child] = item
            else:
                collect_texts(item, child, result)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            collect_texts(item, f"{pointer}/{index}", result)
    return result


def preview(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW_LENGTH else flat[:PREVIEW_LENGTH] + "…"


def report_text_changes(local: bytes, remote: bytes) -> None:
    try:
        import yaml
    except ImportError:
        print("未安装 PyYAML，跳过原文改动位置的列表。")
        return
    old = collect_texts(yaml.safe_load(local))
    new = collect_texts(yaml.safe_load(remote))
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(key for key in old.keys() & new.keys() if old[key] != new[key])
    print()
    print(f"原文文本改动：新增 {len(added)} 处，修改 {len(changed)} 处，删除 {len(removed)} 处")
    print("修改的位置即使生成与校验都通过，对应中文也可能已经过期，必须逐条核对。")
    for title, keys, source in (("新增", added, new), ("修改", changed, new), ("删除", removed, old)):
        for key in keys:
            print(f"- [{title}] {key}")
            if title == "修改":
                print(f"    旧：{preview(old[key])}")
            print(f"    {'新' if title != '删除' else '旧'}：{preview(source[key])}")


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
        report_text_changes(local, remote)
        sys.exit(1)
    print(f"上游 OpenAPI 未变化：sha256={local_hash}")


if __name__ == "__main__":
    main()
