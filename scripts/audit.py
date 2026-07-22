#!/usr/bin/env python3
"""验证中文规格未改变 API 契约，并报告仍含日文的翻译单元。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "fincode-openapi.ja.yml"
TRANSLATED = ROOT / "site" / "spec" / "fincode-openapi.zh-CN.yml"
REPORT = ROOT / "site" / "translation-report.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
TRANSLATABLE_KEYS = {"title", "summary", "description"}


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def operations(document: dict[str, Any]) -> dict[tuple[str, str], str | None]:
    return {
        (path, method): operation.get("operationId")
        for path, path_item in document.get("paths", {}).items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    }


def requires_translation(text: str) -> bool:
    """判断上游文本是否包含需要人工翻译或确认的日文、汉字内容。"""
    return any(
        "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        for char in text
    )


def find_remaining(
    source: Any, translated_value: Any, pointer: str = "", key: str | None = None
) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(source, dict):
        for child_key, child in source.items():
            escaped = str(child_key).replace("~", "~0").replace("/", "~1")
            found.extend(
                find_remaining(child, translated_value[child_key], f"{pointer}/{escaped}", str(child_key))
            )
    elif isinstance(source, list):
        for index, child in enumerate(source):
            found.extend(find_remaining(child, translated_value[index], f"{pointer}/{index}", key))
    elif (
        isinstance(source, str)
        and key in TRANSLATABLE_KEYS
        and source == translated_value
        and requires_translation(source)
    ):
        found.append({"pointer": pointer, "preview": source.replace("\n", " ")[:160]})
    return found


def main() -> None:
    source = load(SOURCE)
    translated = load(TRANSLATED)

    assert source["openapi"] == translated["openapi"], "OpenAPI 版本被改变"
    assert set(source.get("paths", {})) == set(translated.get("paths", {})), "API 路径集合不一致"
    assert operations(source) == operations(translated), "HTTP 方法或 operationId 被改变"
    assert set(source.get("components", {}).get("schemas", {})) == set(
        translated.get("components", {}).get("schemas", {})
    ), "数据模型集合不一致"

    operation_tags = {
        tag
        for path_item in translated.get("paths", {}).values()
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
        for tag in operation.get("tags", [])
    }
    grouped_tags = {
        tag for group in translated.get("x-tagGroups", []) for tag in group.get("tags", [])
    }
    missing_group_tags = operation_tags - grouped_tags
    assert not missing_group_tags, f"导航分组遗漏接口标签：{sorted(missing_group_tags)}"

    remaining = find_remaining(source, translated)
    report = {
        "contractIntegrity": "passed",
        "remainingJapaneseUnits": len(remaining),
        "items": remaining,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contractIntegrity": "passed", "remainingJapaneseUnits": len(remaining)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
