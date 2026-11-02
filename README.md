# fincode 中文参考

这是面向中文开发者的 fincode 非官方中文参考项目。中文内容由维护者结合支付业务与上下文逐条人工翻译，不调用机器翻译或第三方翻译服务。

在线阅读：<https://zhichao-poper.github.io/fincode-docs-cn/>

## 当前范围

- 原文来源：[fincode API Reference](https://docs.fincode.jp/api)
- 上游规格：OpenAPI 3.0.2 / fincode API 1.4.0
- REST API Reference 已完成全量翻译
- 支付指南当前仅覆盖“卡片支付”和“便利店支付”两组，共 13 篇
- 暂不包含其他支付方式、fincode JS 与 SDK 指南；后续按需追加

## 翻译原则

1. API 路径、HTTP 方法、字段名、枚举值、示例值和 `operationId` 不翻译。
2. 标题、说明、参数含义、响应含义与业务注意事项翻译为简体中文。
3. 对可能有歧义的支付术语先统一术语表，再翻译正文。
4. 每条中文译文都能追溯到上游 JSON Pointer；上游新增内容会进入“待翻译”清单。
5. 中文站仅作为辅助参考，发生歧义时以 fincode 官方日文文档为准。

支付指南额外遵循以下约束：

1. 只收录 `scripts/guide_manifest.py` 明确列出的 13 个页面。
2. 流程图、表格、列表和代码字面量必须与日文源页面一一对应。
3. 页头、双层导航、侧栏、正文宽度、字体与响应式断点对齐 fincode 官方文档。
4. 每个中文页面都提供官方日文原文链接。

## 目录

```text
source/                         上游日文 OpenAPI 快照
source/payment-guides.ja.json   指定支付指南的日文内容快照
translations/zh_CN.yml         人工译文与术语映射
translations/payment-guides/   支付指南人工中文译文
scripts/build_spec.py          合并译文并生成中文规格
scripts/audit.py               校验结构一致性与遗漏
scripts/sync_guides.py         更新支付指南日文源与图片
scripts/build_guides.py        生成支付指南静态页面
scripts/audit_guides.py        校验指南范围、结构、字面量与本地链接
site/                           GitHub Pages 静态站
```

## 本地生成

```bash
python3 scripts/build_spec.py
python3 scripts/audit.py
python3 scripts/build_guides.py
python3 scripts/audit_guides.py
python3 -m http.server 4173 --directory site
```

然后访问 <http://localhost:4173/>。

## 内容权利说明

本项目不是 fincode 或 GMO Epsilon 的官方项目。原始 API 文档、产品名称与商标的权利归其各自权利人所有。项目维护方已通过邮件与 fincode 方面确认中文翻译与发布事宜；中文内容仍仅作为开发辅助参考，发生歧义时以官方日文文档为准。
