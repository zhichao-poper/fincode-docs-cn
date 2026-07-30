#!/usr/bin/env python3
"""审计支付指南的范围、结构、代码字面量、图片与中文化完整性。"""

from __future__ import annotations

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from guide_manifest import PAGES

ROOT = Path(__file__).resolve().parents[1]
JAPANESE = re.compile(r"[\u3040-\u30ff]")
STRUCTURAL_TAGS = ("h2", "h3", "h4", "table", "ol", "ul", "img")


class FragmentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: Counter[str] = Counter()
        self.images: list[str] = []
        self.codes: list[str] = []
        self._code_depth = 0
        self._code_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags[tag] += 1
        attributes = dict(attrs)
        if tag == "img" and attributes.get("src"):
            self.images.append(attributes["src"])
        if tag == "code":
            self._code_depth += 1
            self._code_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._code_depth:
            self.codes.append("".join(self._code_buffer))
            self._code_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._code_depth:
            self._code_buffer.append(data)


class SiteReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value:
                self.references.append(value)


def audit_local_references(output_path: Path, errors: list[str]) -> None:
    parser = SiteReferenceParser()
    parser.feed(output_path.read_text(encoding="utf-8"))
    for reference in parser.references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (output_path.parent / unquote(parsed.path)).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            errors.append(
                f"本地链接或资源不存在：{output_path.relative_to(ROOT)} -> {reference}"
            )


def walk_elements(node: object):
    if isinstance(node, dict):
        if node.get("type") == "element":
            yield node
        for value in node.values():
            yield from walk_elements(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_elements(value)


def text_content(node: object) -> str:
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("value", ""))
        return "".join(text_content(value) for value in node.values())
    if isinstance(node, list):
        return "".join(text_content(value) for value in node)
    return ""


def main() -> None:
    errors: list[str] = []
    snapshot_path = ROOT / "source/payment-guides.ja.json"
    if not snapshot_path.exists():
        raise SystemExit("缺少 source/payment-guides.ja.json，请先运行 sync_guides.py")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    source_pages = {page["sourcePath"]: page["document"] for page in snapshot["pages"]}
    expected_paths = {page["source_path"] for page in PAGES}
    if set(source_pages) != expected_paths:
        errors.append("日文源快照的页面集合与清单不一致")
    if snapshot.get("scope", {}).get("pageCount") != len(PAGES):
        errors.append("日文源快照的页面数量不正确")

    for page in PAGES:
        translation_path = ROOT / page["translation"]
        output_path = ROOT / page["output"]
        if not translation_path.exists():
            errors.append(f"缺少译文：{page['translation']}")
            continue
        if not output_path.exists():
            errors.append(f"缺少构建页面：{page['output']}")
            continue
        fragment = translation_path.read_text(encoding="utf-8")
        if JAPANESE.search(fragment):
            errors.append(f"译文仍含日文假名：{page['translation']}")
        parser = FragmentParser()
        parser.feed(fragment)
        if parser.tags["h1"] != 1:
            errors.append(f"译文必须且只能有一个 h1：{page['translation']}")

        source = source_pages[page["source_path"]]
        source_elements = list(walk_elements(source.get("body", {})))
        source_counts = Counter(element.get("tag") for element in source_elements)
        for tag in STRUCTURAL_TAGS:
            if parser.tags[tag] != source_counts[tag]:
                errors.append(
                    f"{page['translation']} 的 {tag} 数量为 {parser.tags[tag]}，"
                    f"日文源为 {source_counts[tag]}"
                )

        source_images = sorted(
            element.get("props", {}).get("src")
            for element in source_elements
            if element.get("tag") == "img"
        )
        if sorted(parser.images) != source_images:
            errors.append(f"图片集合与日文源不一致：{page['translation']}")

        source_code_tokens = Counter(
            token
            for element in source_elements
            if element.get("tag") == "code"
            for token in re.findall(
                r"[A-Za-z][A-Za-z0-9_.:/-]*",
                text_content(element),
            )
        )
        translated_code_tokens = Counter(
            token
            for code in parser.codes
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_.:/-]*", code)
        )
        missing_code_tokens = source_code_tokens - translated_code_tokens
        if missing_code_tokens:
            errors.append(
                f"code 中缺少日文源的 API/品牌字面量：{page['translation']} "
                f"({dict(missing_code_tokens)})"
            )

        output = output_path.read_text(encoding="utf-8")
        if page["source_url"] not in output:
            errors.append(f"构建页面缺少官方原文链接：{page['output']}")
        audit_local_references(output_path, errors)

    landing = ROOT / "site/guides/index.html"
    if not landing.exists():
        errors.append("缺少支付指南目录页")
    else:
        landing_text = landing.read_text(encoding="utf-8")
        expected_entry = Path(PAGES[0]["output"]).relative_to("site/guides")
        if 'http-equiv="refresh"' not in landing_text:
            errors.append("支付指南入口页没有配置跳转")
        if str(expected_entry) not in landing_text:
            errors.append("支付指南入口页没有指向卡片支付首页")
        audit_local_references(landing, errors)

    if errors:
        print("支付指南审计失败：")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        f"支付指南审计通过：{len(PAGES)} 页，"
        "范围仅含卡片支付与便利店支付，结构、图片和代码字面量一致"
    )


if __name__ == "__main__":
    main()
