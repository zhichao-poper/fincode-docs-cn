# fincode API 中文参考

这是面向团队内部开发的 fincode API 中文参考项目。中文内容由维护者结合支付业务与 OpenAPI 上下文逐条人工翻译，不调用机器翻译或第三方翻译服务。

## 当前范围

- 原文来源：[fincode API Reference](https://docs.fincode.jp/api)
- 上游规格：OpenAPI 3.0.2 / fincode API 1.4.0
- 第一阶段仅覆盖 REST API Reference
- 暂不包含 fincode JS、SDK，以及 Docs 中的业务操作指南

## 翻译原则

1. API 路径、HTTP 方法、字段名、枚举值、示例值和 `operationId` 不翻译。
2. 标题、说明、参数含义、响应含义与业务注意事项翻译为简体中文。
3. 对可能有歧义的支付术语先统一术语表，再翻译正文。
4. 每条中文译文都能追溯到上游 JSON Pointer；上游新增内容会进入“待翻译”清单。
5. 中文站仅作为辅助参考，发生歧义时以 fincode 官方日文文档为准。

## 目录

```text
source/                         上游日文 OpenAPI 快照
translations/zh_CN.yml         人工译文与术语映射
scripts/build_spec.py          合并译文并生成中文规格
scripts/audit.py               校验结构一致性与遗漏
site/                           GitHub Pages 静态站
```

## 本地生成

```bash
python3 scripts/build_spec.py
python3 scripts/audit.py
python3 -m http.server 4173 --directory site
```

然后访问 <http://localhost:4173/>。

## 内容权利说明

本项目不是 fincode 或 GMO Epsilon 的官方项目。原始 API 文档、产品名称与商标的权利归其各自权利人所有。仓库暂按团队内部、非公开方式维护；在公开发布完整译文前，应先确认原文转载与翻译授权。

