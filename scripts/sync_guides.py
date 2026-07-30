#!/usr/bin/env python3
"""从 fincode 官方 Nuxt 内容库更新指定支付指南的日文快照与图片。"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from guide_manifest import PAGES

ROOT = Path(__file__).resolve().parents[1]
HOME_URL = "https://docs.fincode.jp/payment/fraud_protection"
ASSET_ORIGIN = "https://docs.fincode.jp"
USER_AGENT = "fincode-docs-cn source sync"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def find_assets(node: object) -> set[str]:
    assets: set[str] = set()
    if isinstance(node, dict):
        if node.get("type") == "element":
            props = node.get("props", {})
            for attribute in ("src", "href", "to"):
                value = props.get(attribute)
                if isinstance(value, str) and value.startswith("/assets/images/"):
                    assets.add(value)
        for value in node.values():
            assets.update(find_assets(value))
    elif isinstance(node, list):
        for value in node:
            assets.update(find_assets(value))
    return assets


def main() -> None:
    home = fetch(HOME_URL).decode("utf-8")
    match = re.search(r'dbHash:"([a-f0-9]+)"', home)
    if not match:
        raise RuntimeError("无法从 fincode 页面确定 Nuxt Content 数据库版本")
    db_hash = match.group(1)
    db_url = f"{ASSET_ORIGIN}/_nuxt/content/db-{db_hash}.json"
    database = json.loads(fetch(db_url))
    documents = {
        item.get("path"): item
        for collection in database.get("_collections", [])
        for item in collection.get("_data", [])
    }

    selected = []
    missing = []
    for page in PAGES:
        document = documents.get(page["source_path"])
        if document is None:
            missing.append(page["source_path"])
            continue
        selected.append(
            {
                "key": page["key"],
                "sourcePath": page["source_path"],
                "sourceUrl": page["source_url"],
                "document": document,
            }
        )
    if missing:
        raise RuntimeError(f"上游缺少目标页面：{', '.join(missing)}")

    snapshot = {
        "source": HOME_URL,
        "databaseUrl": db_url,
        "databaseHash": db_hash,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "group": "決済",
            "sections": ["カード決済", "コンビニ決済"],
            "pageCount": len(selected),
        },
        "pages": selected,
    }
    snapshot_path = ROOT / "source/payment-guides.ja.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    asset_paths = set()
    for page in selected:
        asset_paths.update(find_assets(page["document"].get("body")))
    for asset_path in sorted(asset_paths):
        relative = asset_path.removeprefix("/assets/images/")
        destination = ROOT / "site/assets/payment-guides" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(fetch(ASSET_ORIGIN + asset_path))

    print(
        f"已同步 {len(selected)} 个页面、{len(asset_paths)} 个图片资源，"
        f"Nuxt Content {db_hash}"
    )


if __name__ == "__main__":
    main()
