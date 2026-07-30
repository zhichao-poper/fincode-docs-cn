#!/usr/bin/env python3
"""将人工翻译片段构建为可直接发布到 GitHub Pages 的静态指南。"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

from guide_manifest import PAGES, SECTIONS

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUTPUT_BY_SOURCE_ROUTE = {
    page["source_url"].removeprefix("https://docs.fincode.jp"): page["output"]
    for page in PAGES
}


def relative_url(current_output: Path, target: Path) -> str:
    return os.path.relpath(target, current_output.parent).replace(os.sep, "/")


def rewrite_fragment(fragment: str, output: Path) -> str:
    asset_root = SITE / "assets/payment-guides"

    def replace_image(match: re.Match[str]) -> str:
        relative_asset = match.group(1)
        return f'src="{relative_url(output, asset_root / relative_asset)}"'

    fragment = re.sub(
        r'src="/assets/images/([^"]+)"',
        replace_image,
        fragment,
    )
    fragment = re.sub(
        r'href="/assets/images/([^"]+)"',
        lambda match: (
            f'href="{relative_url(output, asset_root / match.group(1))}"'
        ),
        fragment,
    )
    fragment = re.sub(
        r'href="/api(#[^"]*)?"',
        lambda match: (
            f'href="{relative_url(output, SITE / "reference.html")}'
            f'{match.group(1) or ""}"'
        ),
        fragment,
    )

    def replace_internal_link(match: re.Match[str]) -> str:
        route = match.group(1).rstrip("/")
        anchor = match.group(2) or ""
        target = OUTPUT_BY_SOURCE_ROUTE.get(route)
        if target:
            return f'href="{relative_url(output, ROOT / target)}{anchor}"'
        return f'href="https://docs.fincode.jp{route}{anchor}"'

    fragment = re.sub(
        r'href="(/payment[^"#?]*)(#[^"]*)?"',
        replace_internal_link,
        fragment,
    )
    fragment = re.sub(
        r'href="(/(?!/)[^"]+)"',
        lambda match: f'href="https://docs.fincode.jp{match.group(1)}"',
        fragment,
    )
    return fragment


def navigation(current: dict, output: Path) -> str:
    parts = []
    for section, section_title in SECTIONS.items():
        section_active = ' class="section-active"' if section == current["section"] else ""
        parts.append(
            f'<p class="guide-nav-section"{section_active}>'
            f'<span>{html.escape(section_title)}</span><i aria-hidden="true"></i></p>'
        )
        parts.append('<ul class="guide-nav-list">')
        for page in [item for item in PAGES if item["section"] == section]:
            active = ' aria-current="page" class="active"' if page == current else ""
            href = relative_url(output, ROOT / page["output"])
            parts.append(
                f'<li><a href="{href}"{active}>{html.escape(page["nav_title"])}</a></li>'
            )
        parts.append("</ul>")
    return "\n".join(parts)


def page_template(page: dict, body: str, index: int) -> str:
    output = ROOT / page["output"]
    home = relative_url(output, SITE / "index.html")
    guide_home = relative_url(output, SITE / "guides/index.html")
    stylesheet = relative_url(output, SITE / "guide-styles.css")
    favicon = relative_url(output, SITE / "favicon.svg")
    reference = relative_url(output, SITE / "reference.html")
    breadcrumbs = [
        f'<li><a href="{guide_home}">首页</a></li>',
        f'<li><a href="{guide_home}">支付</a></li>',
        f'<li><a href="{relative_url(output, ROOT / next(item["output"] for item in PAGES if item["section"] == page["section"]))}">{html.escape(SECTIONS[page["section"]])}</a></li>',
    ]
    if page["key"] == "card-3d-secure-2":
        parent = next(item for item in PAGES if item["key"] == "card-fraud-protection")
        breadcrumbs.append(
            f'<li><a href="{relative_url(output, ROOT / parent["output"])}">'
            f'{html.escape(parent["title"])}</a></li>'
        )
    breadcrumbs.append(f'<li aria-current="page">{html.escape(page["title"])}</li>')
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="fincode {html.escape(page["title"])}中文指南。" />
    <title>{html.escape(page["title"])} | fincode 中文参考</title>
    <link rel="icon" href="{favicon}" type="image/svg+xml" />
    <link rel="stylesheet" href="{stylesheet}" />
  </head>
  <body>
    <header class="official-header">
      <div class="official-header-main">
        <div class="official-header-left">
          <a class="fincode-logo" href="{home}" aria-label="fincode 中文参考">
            <img src="https://docs.fincode.jp/assets/images/logos/fincode.svg" alt="fincode by GMO" />
          </a>
          <a class="docs-logo" href="{guide_home}" aria-label="docs">
            <img src="https://docs.fincode.jp/assets/images/text-docs.svg" alt="docs" />
          </a>
        </div>
        <nav class="official-header-links" aria-label="实用链接">
          <a href="{guide_home}">docs</a><span>/</span><a href="{reference}">API reference</a>
          <b aria-hidden="true">|</b>
          <a href="{page["source_url"]}" target="_blank" rel="noreferrer">官方日文原文</a>
          <a href="https://dashboard.fincode.jp/login" target="_blank" rel="noreferrer">登录</a>
          <a class="start-button" href="https://www.fincode.jp/" target="_blank" rel="noreferrer">立即开始</a>
        </nav>
        <details class="mobile-menu">
          <summary>MENU</summary>
          <nav aria-label="手机端导航">
            <a href="{guide_home}">首页</a>
            <a href="{guide_home}">支付</a>
            <a href="{reference}">API reference</a>
            <a href="{page["source_url"]}" target="_blank" rel="noreferrer">官方日文原文</a>
          </nav>
        </details>
      </div>
      <nav class="official-category-nav" aria-label="主要导航">
        <a href="{guide_home}">首页</a>
        <a href="https://docs.fincode.jp/tutorial" target="_blank" rel="noreferrer">教程</a>
        <a class="active" href="{guide_home}">支付</a>
        <a href="https://docs.fincode.jp/business_management" target="_blank" rel="noreferrer">运营管理</a>
        <a href="https://docs.fincode.jp/platform" target="_blank" rel="noreferrer">平台</a>
        <a href="https://docs.fincode.jp/develop_support" target="_blank" rel="noreferrer">开发者支持</a>
        <a href="https://docs.fincode.jp/buyer_service" target="_blank" rel="noreferrer">买家服务</a>
        <a href="https://docs.fincode.jp/releases" target="_blank" rel="noreferrer">发行说明</a>
        <span class="header-search" aria-hidden="true"></span>
      </nav>
    </header>
    <div class="guide-layout">
      <aside class="guide-sidebar" aria-label="支付指南目录">
        <a class="guide-overview-link" href="{guide_home}"><span>支付</span><i aria-hidden="true"></i></a>
        {navigation(page, output)}
      </aside>
      <div class="guide-body">
        <nav class="guide-breadcrumb" aria-label="面包屑">
          <ul>{''.join(breadcrumbs)}</ul>
        </nav>
        <main class="guide-main">
          <article class="guide-article">
{body}
          </article>
          <p class="guide-source-note">本页为非官方中文翻译；如有歧义，请以<a href="{page["source_url"]}" target="_blank" rel="noreferrer">官方日文原文</a>为准。</p>
        </main>
      </div>
    </div>
  </body>
</html>
"""


def build_landing() -> None:
    output = SITE / "guides/index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    first_page = relative_url(output, ROOT / PAGES[0]["output"])
    output.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="fincode 卡片支付与便利店支付中文指南。" />
    <title>支付指南 | fincode 中文参考</title>
    <meta http-equiv="refresh" content="0; url={first_page}" />
    <link rel="canonical" href="{first_page}" />
  </head>
  <body>
    <p>正在进入<a href="{first_page}">卡片支付中文指南</a>……</p>
  </body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    for index, page in enumerate(PAGES):
        translation = ROOT / page["translation"]
        if not translation.exists():
            raise RuntimeError(f"缺少人工译文：{translation.relative_to(ROOT)}")
        output = ROOT / page["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        body = rewrite_fragment(translation.read_text(encoding="utf-8"), output)
        rendered = page_template(page, body, index)
        rendered = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
        output.write_text(rendered, encoding="utf-8")
    build_landing()
    print(f"已生成 {len(PAGES)} 个支付指南页面和 1 个目录页")


if __name__ == "__main__":
    main()
