# 答辩 PPT 草稿

本文件是正式 `答辩PPT.pptx` 制作前的逐页草稿，可直接复制到 PowerPoint 或 WPS 演示中。

## 第 1 页：标题页

- 视频学习资源智能筛选系统
- 引导案例：PCA 主成分分析学习资源筛选
- 技术关键词：Python、B 站、YouTube、LLM、CSV/Markdown、Streamlit

## 第 2 页：项目背景

- 网络学习资源数量多，但质量参差不齐。
- 教师备课时需要跨平台手动搜索和筛选视频，效率低。
- 项目目标是把“学习资源筛选”变成可复用的工程流水线。

## 第 3 页：系统目标

- 输入任意学习主题。
- 自动检索 B 站和 YouTube 候选视频。
- 抓取元数据与字幕。
- 调用 LLM 输出结构化教学价值评估。
- 导出 CSV、JSON、Markdown 和运行日志。

## 第 4 页：系统架构

- `main.py`：命令行调度。
- `search_bilibili.py` / `search_youtube.py`：平台检索。
- `evaluate.py`：OpenAI 兼容接口评估。
- `exporters.py`：多格式导出。
- `cache_utils.py`：缓存层。
- `app.py`：Streamlit UI。

## 第 5 页：核心数据字段

- 视频基础字段：platform、title、url、author、view、like、duration。
- 字幕字段：has_subtitle、subtitle_text、subtitle_language、subtitle_source。
- LLM 字段：relevance、depth、clarity、has_math、has_code、audience、recommend、reason。

## 第 6 页：LLM 评估设计

- 使用严格 JSON 输出，便于后续程序处理。
- 通过 Pydantic 校验字段和取值范围。
- 失败样本不阻断整批流程。
- Prompt 经过无字幕和短视频场景迭代。

## 第 7 页：当前验收结果

- `pytest`：44 passed。
- `ruff check .`：通过。
- `black --check .`：通过。
- 人工对照 10 条，一致率 80%，达到任务书 ≥70%。
- B 站小样本和抖音参考数据流程均可导出 CSV/JSON/Markdown/log。

## 第 8 页：风险与解决思路

- B 站和 YouTube 字幕成功率受平台与网络环境影响。
- YouTube transcript API 版本变化已修复并加测试。
- ASR 兜底已实现基础逻辑，但仍需真实小样本验证。
- 抖音抓取工程代价高，作为参考 JSON 接入主流程。

## 第 9 页：演示流程

- 运行测试和静态检查。
- 运行 B 站小样本。
- 展示 Markdown 推荐清单。
- 运行抖音参考数据流程。
- 启动 Streamlit UI。
- 如已配置 `.env`，演示 B 站 + YouTube 完整流程。

## 第 10 页：总结

- 项目完成了从检索、抓取、评估到导出的完整工程链路。
- 最大难点是外部平台的不稳定性和字幕覆盖率。
- 后续可继续加强 ASR、UI、定时批处理和更多课程主题适配。
