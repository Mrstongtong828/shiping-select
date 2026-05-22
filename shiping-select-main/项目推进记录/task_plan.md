# 视频筛选项目推进计划

## 目标

把当前代码从“核心主线可运行”推进到“可按项目书验收提交”的状态。

## 阶段

1. 已完成：确认 Python 3.14.5 虚拟环境可用，基础测试通过。
2. 已完成：运行 B 站最小流程，生成 PCA 主题的 CSV / JSON / Markdown / log。
3. 已完成：同步 README 与当前代码状态，整理验收缺口。
4. 已完成：配置 `.env` 后运行 YouTube + LLM 完整流程，生成可评估样例。
5. 进行中：生成最终输出样例、Prompt 迭代记录、人工对照评估表、反思报告和答辩材料。
6. 已完成：人工抽样 10 条对照评估，一致率 80%，达到项目书要求。

## 当前约束

- 当前主项目没有 `.env`，所以不能运行 YouTube 搜索和 LLM 评估。
- `.env` 已配置真实 Key。
- YouTube 搜索和 LLM 评估可运行，但 YouTube transcript 受当前网络出口限制，字幕成功数为 0。
- B 站最小流程可运行，但短时间连续请求可能触发 412 风控。
- 抖音代码是独立原型，暂不并入主线。

## 错误记录

| 问题 | 现象 | 当前处理 |
| --- | --- | --- |
| `pytest.exe` 找不到 `src` | 直接运行 `pytest.exe` 报 `ModuleNotFoundError` | 使用 `python -m pytest` 可通过 |
| B 站字幕为 0 | 15 条 PCA 结果均无字幕 | 初步判断为公开视频字幕字段为空，后续用 YouTube/ASR/降级评估补足 |
| 无 `.env` | 缺少 YouTube 和 LLM Key | 先推进文档和清单，待 Key 配置后跑完整流程 |
| 不是 Git 仓库 | `git status` / `git diff` 无法使用 | 当前按文件清单与测试结果追踪进度 |
| YouTube 搜索超时 | `google-api-python-client` 不稳定走代理 | 改为 `httpx` REST API 调用 |
| YouTube 字幕失败 | `youtube-transcript-api` 旧接口不可用且当前出口 `IpBlocked` | 已兼容新版接口；真实字幕需更换出口或后续 ASR 兜底 |
