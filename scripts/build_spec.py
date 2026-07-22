#!/usr/bin/env python3
"""将人工译文覆盖到上游 OpenAPI，并生成供中文站使用的规格文件。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "fincode-openapi.ja.yml"
TRANSLATIONS = ROOT / "translations" / "zh_CN.yml"
OUTPUT = ROOT / "site" / "spec" / "fincode-openapi.zh-CN.yml"
PROGRESS = ROOT / "site" / "progress.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
TRANSLATABLE_KEYS = {"title", "summary", "description"}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def decode_pointer(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer 必须以 / 开头：{pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def set_pointer(document: Any, pointer: str, value: str) -> None:
    current = document
    parts = decode_pointer(pointer)
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        if last not in current:
            raise KeyError(f"上游不存在翻译目标：{pointer}")
        current[last] = value


def replace_exact_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: replace_exact_strings(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_exact_strings(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def translate_tags(document: dict[str, Any], names: dict[str, str]) -> None:
    for tag in document.get("tags", []):
        tag["name"] = names.get(tag.get("name"), tag.get("name"))
    for path_item in document.get("paths", {}).values():
        for method, operation in path_item.items():
            if method in HTTP_METHODS and isinstance(operation, dict):
                operation["tags"] = [names.get(tag, tag) for tag in operation.get("tags", [])]


def has_japanese_kana(text: str) -> bool:
    return any("\u3040" <= char <= "\u30ff" for char in text)


def count_units(source: Any, translated_value: Any, key: str | None = None) -> tuple[int, int]:
    total = translated = 0
    if isinstance(source, dict):
        for child_key, child in source.items():
            child_total, child_translated = count_units(child, translated_value[child_key], child_key)
            total += child_total
            translated += child_translated
    elif isinstance(source, list):
        for index, child in enumerate(source):
            child_total, child_translated = count_units(child, translated_value[index], key)
            total += child_total
            translated += child_translated
    elif isinstance(source, str) and key in TRANSLATABLE_KEYS:
        total = 1
        translated = int(source != translated_value and not has_japanese_kana(translated_value))
    return total, translated


def main() -> None:
    source = load_yaml(SOURCE)
    translations = load_yaml(TRANSLATIONS)
    result = copy.deepcopy(source)

    result = replace_exact_strings(result, translations.get("exact_strings", {}))
    translate_tags(result, translations.get("tag_names", {}))
    for pointer, text in translations.get("strings", {}).items():
        set_pointer(result, pointer, text)

    result["info"]["x-translation"] = {
        "language": "zh-CN",
        "method": "manual",
        "source": translations["meta"]["source_url"],
        "disclaimer": "中文仅供开发参考；如有歧义，以 fincode 官方日文文档为准。",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(result, handle, allow_unicode=True, sort_keys=False, width=120)

    total, translated = count_units(source, result)
    operations = sum(
        1
        for path_item in result.get("paths", {}).values()
        for method in path_item
        if method in HTTP_METHODS
    )
    progress = {
        "sourceVersion": result["info"]["version"],
        "paths": len(result.get("paths", {})),
        "operations": operations,
        "translationUnits": total,
        "translatedUnits": translated,
        "remainingUnits": total - translated,
        "percentage": round(translated / total * 100, 1) if total else 100,
    }
    PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(progress, ensure_ascii=False))


if __name__ == "__main__":
    main()
