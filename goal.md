# Goal: 完成视频学习资源智能筛选系统终验与加分项

## Objective

将当前根目录开发版项目推进到可按《视频学习资源智能筛选系统_项目实施方案书_v2》终验提交的状态：系统能通过命令行输入学习主题，自动从 B 站、YouTube 检索候选视频，获取元数据与字幕，必要时使用 ASR 兜底，调用 LLM 进行教学价值评估，并导出可交付的 CSV、JSON、Markdown 和运行日志。同时补齐缓存、抖音抓取整合、Streamlit UI 等加分项。

## Current Baseline

当前以仓库根目录开发版为主基准，不以 `shiping-select-main/` 副本为主基准。

已具备的基础能力：

- B 站视频搜索与元数据抓取。
- YouTube 视频搜索与元数据抓取。
- YouTube transcript / B 站字幕抓取逻辑。
- LLM 结构化评估逻辑。
- CSV / JSON / Markdown / run log 导出。
- 本地缓存雏形：搜索、字幕、评估缓存。
- ASR 兜底雏形：`yt-dlp` + `faster-whisper`。
- 人工对照评估记录：10 条样本一致率 80%，达到任务书 ≥70% 要求。

本轮已完成的基础修复：

- 已创建 `.venv` 并安装 `requirements.txt`。
- 已修复根目录开发版的核心中文文案、Prompt、枚举和 Markdown 导出乱码。
- 已新增项目配置，测试和格式检查以根目录开发版为基准，不被资料包副本干扰。
- 已通过 `py_compile`、`pytest`、`ruff` 和 `black --check`，当前测试数为 53。
- 已修复 `youtube-transcript-api` 新版接口兼容问题，改为 `YouTubeTranscriptApi().list(...)`。
- 已将 `douyin` 和 `all` 接入 CLI 平台参数，并支持读取抖音参考爬虫导出的 JSON。
- 已新增 `文档/抖音抓取降级说明与工程代价对比.md`，说明抖音加分项的可运行降级方案、人工登录/风控边界和工程代价对比。
- 已新增 `app.py`，提供 Streamlit 本地 Web UI 入口。
- 已在根目录新增 `文档/`、`评估表/`、`答辩/`、`输出样例/` 终验提交材料结构。
- 已新增文档提交说明、验收状态表、Prompt 迭代记录、反思报告、周报、人工对照评估表、答辩大纲和演示录屏说明。
- 已新增 `scripts/acceptance_check.py` 离线终验自检脚本。
- 离线终验自检已覆盖 README 可复现性、CLI 功能入口、输出样例 CSV 字段、JSON 合法性、Markdown 分层、运行日志、缓存、缓存自检工具、ASR、ASR 环境自检工具、抖音整合、抖音降级说明、Streamlit UI、Streamlit UI 自检工具、文档提交清单、终验前置检查工具、提交样例刷新工具、提交包工具、忽略规则、环境模板、仓库密钥扫描和依赖覆盖。
- 已新增 `文档/终验运行记录.md`，记录本机已通过命令、B 站小样本、Streamlit 基础加载和剩余终验动作。
- 已新增 `scripts/preflight_check.py`，用于真实复跑前检查 `.env`、必要 Key、代理和抖音参考 JSON，且不输出密钥原文。
- 已新增 `scripts/run_final_acceptance.py`，用于在真实 Key 到位后编排严格前置检查、双平台真实运行、提交样例刷新、严格自检、审计报告、演示视频和提交包生成。
- 已新增 `scripts/refresh_submission_samples.py`，用于真实双平台结果达标后刷新最终提交样例，并校验 run log、CSV 字段和 B 站/YouTube 平台覆盖，避免半成品覆盖。
- 已新增 `scripts/package_submission.py`，用于生成终验提交 zip，并排除 `.env`、虚拟环境、运行结果和缓存。
- 已新增 `scripts/final_audit.py`，用于基于离线自检结果生成 `文档/终验审计报告.md`，集中呈现通过项、待补齐项和当前终验结论。
- 已新增 `scripts/generate_demo_recording.py`，用于基于 `ffmpeg` 生成 `答辩/演示录屏.mp4`，展示当前可复验证据和真实 Key 复跑边界。
- 已新增 `scripts/verify_cache.py`，用于离线验证缓存未命中、写入命中和清理后未命中。
- 已新增 `scripts/verify_asr.py`，用于离线检查 `yt-dlp`、`faster-whisper` 和 ASR 默认配置。
- 已新增 `scripts/verify_streamlit_ui.py`，用于 headless 验证 Streamlit UI 本地 HTTP 入口。
- 已新增 `答辩/答辩PPT.md` 作为正式 PPT 制作草稿。
- 已生成 `答辩/答辩PPT.pptx`，可作为答辩演示初版。

当前主要未完成项：

- 根目录当前没有 `.env`，YouTube 搜索和 LLM 评估尚未在本轮完整复跑。
- B 站小样本流程可运行并能导出结果，但字幕成功数为 0，字幕成功率 ≥80% 尚未达成。
- ASR 兜底已有雏形，但还需要小样本验证并确认可提升无字幕视频覆盖。
- 抖音目前是“读取导出 JSON 的参考整合”，真实网页登录抓取仍需要人工登录和参考脚本配合。
- Streamlit UI 已有入口，并已完成本地 HTTP 200 基础加载验收；已生成自动演示说明视频，如需更强证据可替换为真实浏览器操作录屏。
- 最终提交材料仍需补齐真实双平台完整输出样例。

## Missing Features And Acceptance Standards

### P0: 终验硬性要求

1. 修复中文乱码

验收标准：

- `README.md`、`prompts/eval_template.txt`、`src/schema.py`、`src/exporters.py` 中所有中文可正常显示。
- Markdown 输出中的分层标题为：入门理解层、数学推导层、代码实操层、应用案例层。
- LLM `audience` 枚举为：科普、本科入门、本科进阶、研究生。
- `python -m py_compile main.py src/*.py` 通过。

2. 双平台完整流水线

验收标准：

- 命令可运行：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
```

- 单次运行返回候选视频总数 ≥30，或在网络/API 限制下有明确错误日志和降级说明。
- B 站与 YouTube 至少各返回一批有效候选。
- CSV 输出包含任务书要求字段：`platform,title,url,author,view,like,has_subtitle,relevance,depth,clarity,audience,recommend,reason`。
- JSON 和 Markdown 同步生成。
- run log 记录总数、字幕成功数、评估成功数、错误数。

3. 字幕获取与 ASR 兜底

验收标准：

- 优先使用平台字幕。
- 对无字幕视频，在 `--enable-asr` 开启时触发 ASR。
- ASR 成功后写入 `subtitle_text`、`subtitle_language`、`subtitle_source=whisper_asr`。
- 对 PCA 主题 30 条样本，字幕成功率目标 ≥80%；若因 YouTube 网络出口、B 站风控导致无法达标，必须在运行日志和反思报告中说明，并提供 ASR 小样本验证结果。

4. LLM 结构化评估

验收标准：

- 使用 OpenAI 兼容接口，支持 DeepSeek。
- 使用 `response_format={"type": "json_object"}`。
- 输出字段包括：`relevance`、`depth`、`clarity`、`has_math`、`has_code`、`audience`、`recommend`、`reason`。
- JSON 解析失败自动重试。
- 30 条样本评估成功率 ≥90%；失败样本不能中断整批流程。
- 人工抽样 10 条一致率 ≥70%，保留对照表和结论。

5. Markdown 推荐清单

验收标准：

- 输出 `results/pca_主成分分析.md`。
- 按入门理解层、数学推导层、代码实操层、应用案例层分组。
- 包含推荐学习路径。
- 每条推荐包含标题、URL、平台、作者、评分、适用对象和推荐理由。
- 内容可直接给教师或学生阅读，不含乱码。

6. 工程质量

验收标准：

- 创建或修复虚拟环境。
- 安装 `requirements.txt` 成功。
- `python -m pytest` 通过，测试数 ≥3。
- `python -m ruff check .` 通过。
- `python -m black --check .` 通过。
- 关键函数补充简洁 docstring。
- `.env`、缓存、结果目录不进入 Git。

7. 可复现性

验收标准：

- README 写清楚安装、API Key 配置、代理配置、运行命令和测试命令。
- 新机器按 README 操作，能在 5 分钟内完成首次可运行验证。
- `.env.example` 不包含真实 Key。
- `requirements.txt` 覆盖必装和加分项依赖。

8. 最终提交材料

验收标准：

- 输出样例目录包含 `pca_主成分分析.csv`、`pca_主成分分析.json`、`pca_主成分分析.md`、`eval_log.txt` 或等价 run log。
- 文档目录包含 README、反思报告、Prompt 迭代记录、人工对照评估表、Week01 至 Week04 周报。
- 文档目录包含由 `python scripts\final_audit.py` 生成的 `终验审计报告.md`，汇总通过项、待补齐项和当前结论。
- 反思报告不少于 1500 字。
- Prompt 迭代记录至少 3 版。
- 答辩目录包含答辩 PPT 和演示录屏，或可替代的现场演示说明。

### P1: 加分项

1. 缓存层

验收标准：

- 搜索结果、字幕结果、LLM 评估结果均可缓存。
- 支持 `--no-cache` 禁用缓存。
- 支持 `--clear-cache` 清空缓存。
- 重复运行同一主题时减少 API 和 LLM 调用。

2. 抖音抓取整合

验收标准：

- 参考 `douyinpachong-main/`，在 `src/search_douyin.py` 中提供统一接口。
- CLI 支持 `--platform douyin` 和 `--platform bilibili,youtube,douyin`。
- 抖音模块至少返回标题、URL、作者、播放/点赞可得字段。
- 若平台限制导致无法稳定抓取，必须提供可运行的降级说明和工程代价对比文档。

3. Streamlit UI

验收标准：

- 新增本地 Web UI。
- 支持输入主题、选择平台、设置 max、选择是否评估、选择是否 ASR。
- 支持填写或读取 YouTube API Key、OpenAI compatible API、Base URL、Model、代理端口。
- 点击按钮后运行筛选流程并展示结果表。
- 支持下载 CSV / Markdown。

4. ASR 完整化

验收标准：

- 支持 CPU 模式默认运行。
- 支持环境变量 `ASR_MODEL`、`ASR_COMPUTE_TYPE`。
- ASR 临时音频自动清理。
- 小样本验证至少 1 条无字幕视频可生成转写文本。

## Verification Commands

基础语法检查：

```powershell
python -m py_compile main.py src\asr_whisper.py src\cache_utils.py src\evaluate.py src\exporters.py src\logging_utils.py src\schema.py src\search_bilibili.py src\search_douyin.py src\search_youtube.py
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

测试：

```powershell
python -m pytest
```

静态检查：

```powershell
python -m ruff check .
python -m black --check .
```

B 站最小流程：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili --max 15 --skip-evaluate
```

双平台完整流程：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
```

ASR 兜底小样本：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 5 --enable-asr --no-cache
```

缓存验证：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10 --clear-cache
```

UI 验证：

```powershell
streamlit run app.py
```

终验审计报告：

```powershell
python scripts\final_audit.py
```

演示说明视频：

```powershell
python scripts\generate_demo_recording.py
```

终验复跑编排：

```powershell
python scripts\run_final_acceptance.py --dry-run
python scripts\run_final_acceptance.py --enable-asr
```

## Completion Criteria

该 goal 仅在以下条件全部满足后视为完成：

- P0 终验硬性要求全部达成。
- P1 加分项中至少完成缓存层、ASR 完整化、Streamlit UI，并尽量完成抖音抓取整合。
- 所有验证命令有明确通过记录，或对外部网络/API 限制有明确说明。
- `文档/终验审计报告.md` 已生成，且与最新 `acceptance_check.py` 自检结果一致。
- 最终输出样例、文档、评估表、答辩材料齐全。
- 仓库中无真实 API Key、Token、Cookie、账号密码。
- 根目录开发版与最终提交目录结构关系清晰，README 中明确说明从哪个目录运行项目。

## Constraints

- 不提交 `.env`、`.venv`、`results/cache/`、`__pycache__/`、`.pytest_cache/`。
- 不覆盖用户已有真实配置文件。
- 不删除历史资料包，除非用户明确要求。
- 外部平台请求必须限速，避免高频抓取。
- 不为了字幕成功率保存完整长字幕到最终 CSV/Markdown，避免版权风险。
