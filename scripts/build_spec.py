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
JSON_OUTPUT = ROOT / "site" / "spec" / "fincode-openapi.zh-CN.json"
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


def normalize_translation_key(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def replace_exact_strings(
    value: Any, replacements: dict[str, str], normalized_replacements: dict[str, str]
) -> Any:
    if isinstance(value, dict):
        return {
            key: replace_exact_strings(item, replacements, normalized_replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [replace_exact_strings(item, replacements, normalized_replacements) for item in value]
    if isinstance(value, str):
        if value in replacements:
            return replacements[value]
        normalized = normalize_translation_key(value)
        if normalized in normalized_replacements:
            return normalized_replacements[normalized]
        return value
    return value


def translate_property_descriptions(value: Any, descriptions: dict[str, str]) -> None:
    """按稳定字段名复用人工译文，覆盖普通属性和 ReDoc 扩展请求属性。"""
    if isinstance(value, dict):
        for container_key in ("properties", "x-req-properties"):
            properties = value.get(container_key)
            if not isinstance(properties, dict):
                continue
            for name, schema in properties.items():
                if (
                    name in descriptions
                    and isinstance(schema, dict)
                    and isinstance(schema.get("description"), str)
                ):
                    schema["description"] = descriptions[name]
        for child in value.values():
            translate_property_descriptions(child, descriptions)
    elif isinstance(value, list):
        for child in value:
            translate_property_descriptions(child, descriptions)


def translate_named_schema_descriptions(
    document: dict[str, Any], descriptions: dict[str, str]
) -> None:
    """同名独立 Schema 与请求属性共享同一份人工字段释义。"""
    schemas = document.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict):
        return
    for name, description in descriptions.items():
        schema = schemas.get(name)
        if isinstance(schema, dict) and isinstance(schema.get("description"), str):
            schema["description"] = description


def translate_tags(
    document: dict[str, Any], names: dict[str, str], group_names: dict[str, str]
) -> None:
    for tag in document.get("tags", []):
        tag["name"] = names.get(tag.get("name"), tag.get("name"))
    for path_item in document.get("paths", {}).values():
        for method, operation in path_item.items():
            if method in HTTP_METHODS and isinstance(operation, dict):
                operation["tags"] = [names.get(tag, tag) for tag in operation.get("tags", [])]
    for group in document.get("x-tagGroups", []):
        group["name"] = group_names.get(group.get("name"), group.get("name"))
        group["tags"] = [names.get(tag, tag) for tag in group.get("tags", [])]


def requires_translation(text: str) -> bool:
    """英文产品名、API 术语等无需改写；含日文假名或汉字的上游文本需要人工确认。"""
    return any(
        "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        for char in text
    )


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
        translated = int(source != translated_value or not requires_translation(source))
    return total, translated


def main() -> None:
    source = load_yaml(SOURCE)
    translations = load_yaml(TRANSLATIONS)
    result = copy.deepcopy(source)

    exact_strings = translations.get("exact_strings", {})
    normalized_exact_strings = {
        normalize_translation_key(key): value for key, value in exact_strings.items()
    }
    result = replace_exact_strings(result, exact_strings, normalized_exact_strings)
    translate_property_descriptions(
        result,
        translations.get("property_descriptions", {}),
    )
    translate_named_schema_descriptions(
        result,
        translations.get("property_descriptions", {}),
    )
    translate_tags(
        result,
        translations.get("tag_names", {}),
        translations.get("tag_group_names", {}),
    )
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
    JSON_OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

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
