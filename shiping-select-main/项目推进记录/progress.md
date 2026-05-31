# 项目推进日志

## 2026-05-18

- 确认 Python 3.14.5 与 `.venv` 可用。
- 运行 `python -m pytest`，结果：3 passed。
- 运行 B 站最小流程：

```powershell
.\.venv\Scripts\python.exe main.py --topic "PCA 主成分分析" --platform bilibili --max 15 --skip-evaluate
```

- 生成 `results/PCA_主成分分析.csv`、`.json`、`.md` 和 `_run.log`。

## 2026-05-20

- 阅读新增 `douyinpachong-main`，判断其为独立抖音爬虫原型，暂不并入主线。
- 检查主项目配置，当前没有 `.env`。
- 重新运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 结果：3 passed。
- 更新 `README.md`，同步 LLM 评估已经接入、完整流程需要 `.env`、测试推荐使用 `python -m pytest` 等信息。
- 新增 `docs/验收推进清单.md`，对照项目书整理当前缺口与推荐执行顺序。
- 新增 `task_plan.md`、`findings.md`、`progress.md`，用于后续持续追踪项目推进。
- 再次运行测试，结果：3 passed。
- 尝试查看 Git 状态，发现当前目录不是 Git 仓库，后续以文件清单和测试结果追踪。

## 2026-05-20 后续

- 创建 `.env` 占位文件，等待填入 `YOUTUBE_API_KEY` 和 `OPENAI_API_KEY`。
- 新增 `文档/Prompt迭代记录.md`，用于后续记录至少 3 版 Prompt。
- 新增 `文档/反思报告.md` 初稿框架。
- 新增 `评估表/人工对照评估表.csv`，用于后续抽样 10 条做人工对照。

## 2026-05-20 完整链路验证

- 配置 `.env` 后，确认 `YOUTUBE_API_KEY`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 均已配置。
- 首次完整运行时，LLM 评估成功，但 YouTube 搜索因连接超时失败。
- 将 YouTube 搜索模块从 `google-api-python-client` 改为 `httpx` REST API 调用，并新增 `tests/test_youtube.py`。
- 修复 `youtube-transcript-api` 新版本接口兼容问题，改为 `YouTubeTranscriptApi().fetch(...)`。
- 运行测试，结果：5 passed。
- 运行 YouTube 单平台完整流程：

```powershell
$env:HTTP_PROXY='http://127.0.0.1:<PROXY_PORT>'
$env:HTTPS_PROXY='http://127.0.0.1:<PROXY_PORT>'
$env:ALL_PROXY='http://127.0.0.1:<PROXY_PORT>'
.\.venv\Scripts\python.exe main.py --topic "PCA 主成分分析" --platform youtube --max 15
```

- 结果：`total_records=15`，`evaluation_success_count=15`，`errors=0`。
- 仍存在问题：YouTube transcript 抓取被当前网络出口限制，`subtitle_success_count=0`。

## 2026-05-20 人工对照评估

- 用户已完成人工筛选 10 条视频。
- 对照结果：8 条一致，2 条不一致。
- 一致率：80%。
- 项目书要求：≥70%，当前结果达标。
- 新增 `评估表/人工对照评估结果.md` 保存统计结论。
- 更新 `文档/Prompt迭代记录.md`，记录无字幕偏保守和短视频入门资源识别两个问题。
- 根据人工对照结果更新 `prompts/eval_template.txt`：无字幕不再直接否定；短视频可作为科普入门材料，但需在理由中说明局限。
- 运行测试，结果：5 passed。
