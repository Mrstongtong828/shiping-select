# Week02 周报

## 本周目标

接入 YouTube 与 LLM 评估，形成双平台候选资源评估链路。

## 已完成

- 实现 YouTube 搜索与视频详情获取。
- 实现 OpenAI 兼容接口评估。
- 设计 `prompts/eval_template.txt`，要求模型输出严格 JSON。
- 初步完成测试和运行日志。

## 风险

- YouTube transcript 可能受网络出口限制。
- `.env` 中 API Key 不能提交，需要使用 `.env.example` 说明配置。

## 下周计划

- 做人工对照评估。
- 根据误判案例迭代 Prompt。
- 增加缓存层和异常处理。
