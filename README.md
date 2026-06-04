# 视频学习资源智能筛选系统

这是一个面向教学场景的视频学习资源筛选项目。系统输入一个学习主题后，可以从 B 站和 YouTube 检索候选视频，抓取元数据与字幕，并调用 OpenAI 兼容的大模型接口评估视频是否适合作为学习资源，最终导出 CSV、JSON、Markdown 和运行日志。

当前仓库根目录是主要开发版；`shiping-select-main/` 是远端资料包中的整理副本；`douyinpachong-main/` 是抖音抓取参考代码，后续可整合进主工作流。

## 当前能力

- B 站视频搜索与元数据抓取。
- B 站字幕抓取。
- YouTube 视频搜索与元数据抓取。
- YouTube transcript 抓取。
- 统一视频数据结构。
- LLM 结构化评估。
- CSV / JSON / Markdown / 运行日志导出。
- 搜索、字幕、评估结果缓存。
- ASR 兜底雏形：`yt-dlp` + `faster-whisper`。
- 抖音参考 JSON 接入主流程，并提供降级说明与工程代价对比文档。
- 终验审计报告和自动生成的答辩演示说明视频。

## 当前重点

项目正在按 [goal.md](goal.md) 推进，优先完成任务书终验要求：

- 修复中文乱码。
- 跑通 B 站 + YouTube 双平台完整流水线。
- 提升字幕成功率，必要时启用 ASR 兜底。
- 保证 LLM 输出合法 JSON，并完成推荐评估。
- 生成可交付的 CSV、Markdown 和运行日志。
- 补齐测试、静态检查、README、反思报告、Prompt 迭代记录、人工评估表和答辩材料。

## 项目结构

```text
video-finder/
|- .env.example
|- goal.md
|- main.py
|- prompts/
|  |- eval_template.txt
|- requirements.txt
|- results/
|- src/
|  |- asr_whisper.py
|  |- cache_utils.py
|  |- evaluate.py
|  |- exporters.py
|  |- logging_utils.py
|  |- schema.py
|  |- search_bilibili.py
|  |- search_douyin.py
|  |- search_youtube.py
|- tests/
```

## 环境准备

建议使用 Python 3.11 或以上版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

复制环境变量模板：

```powershell
copy .env.example .env
```

至少需要按需配置：

```env
YOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_compatible_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
ASR_MODEL=small
ASR_COMPUTE_TYPE=int8
ASR_DEVICE=cpu
DOUYIN_SAMPLE_JSON=douyinpachong-main/foshan_hot_videos.json
```

如果只验证 B 站检索链路，可以不配置 YouTube 和 LLM Key，并使用 `--skip-evaluate`。
如果 `.env` 仍保留 `your_...`、`replace_...` 等模板占位符，系统会按“未配置”处理，避免把占位符当作真实 Key 请求 YouTube 或 OpenAI 兼容接口。

YouTube 搜索默认优先使用官方 YouTube Data API。若暂时无法获取 `YOUTUBE_API_KEY`，程序会尝试使用 `yt-dlp` 的 `ytsearch` 作为搜索降级入口，仍然输出统一的 `youtube` 平台记录，并继续尝试 YouTube transcript / ASR 字幕兜底。该降级依然依赖本机能访问 YouTube；正式终验仍需以真实运行日志证明 B 站 + YouTube 30 条输出达标。

## 代理配置

如果 YouTube、OpenAI 兼容接口或 ASR 音频下载需要代理，可以在当前 PowerShell 会话中设置：

```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
$env:ALL_PROXY="http://127.0.0.1:7890"
```

将 `7890` 替换成本机代理端口。Streamlit UI 也提供“本地代理端口”输入框，会自动写入 `HTTP_PROXY`、`HTTPS_PROXY` 和 `ALL_PROXY`。

## 运行方式

B 站最小流程：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili --max 15 --skip-evaluate
```

B 站 + YouTube 完整流程：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
```

使用全部已接入平台：

```powershell
python main.py --topic "PCA 主成分分析" --platform all --max 30
```

抖音参考数据流程：

```powershell
python main.py --topic "佛山中考数学" --platform douyin --max 5 --skip-evaluate
```

说明：抖音真实抓取依赖 `douyinpachong-main/` 中的浏览器监听脚本和人工登录。主流程默认读取 `DOUYIN_SAMPLE_JSON` 指向的导出 JSON，并转换为统一结果结构。平台限制、降级运行方式和工程代价对比见 `文档/抖音抓取降级说明与工程代价对比.md`。

跳过 LLM 评估：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30 --skip-evaluate
```

启用 ASR 兜底：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10 --enable-asr
```

禁用缓存或清空缓存：

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10 --no-cache
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 10 --clear-cache
```

启动本地 Web UI：

```powershell
streamlit run app.py
```

## 5 分钟本地验证

新机器或答辩前可以先运行以下命令，确认离线功能、格式检查和材料结构正常：

```powershell
python -m pip install -r requirements.txt
python -m py_compile main.py src\asr_whisper.py src\cache_utils.py src\evaluate.py src\exporters.py src\logging_utils.py src\schema.py src\search_bilibili.py src\search_douyin.py src\search_youtube.py
python -m pytest
python -m ruff check .
python -m black --check .
python scripts\verify_asr.py
python scripts\verify_cache.py
python scripts\verify_streamlit_ui.py
python scripts\preflight_check.py
python scripts\acceptance_check.py
python scripts\final_audit.py --help
python scripts\generate_demo_recording.py --help
python scripts\run_final_acceptance.py --dry-run
python scripts\package_submission.py --help
```

在没有真实 `.env` 和双平台 30 条完整输出前，`acceptance_check.py` 会保留对应 `WARN`，但不影响离线自检通过。

离线自检还会扫描仓库文本文件中常见的 OpenAI、Google、GitHub、Bearer、Cookie/Session 密钥形态；扫描结果只报告文件位置和类型，不输出密钥原文。

抖音加分项的验收边界也已纳入离线自检：自检会确认存在可运行的 `--platform douyin` 降级命令、`DOUYIN_SAMPLE_JSON` 接入说明、人工登录/风控边界和工程代价对比。

缓存层可用以下命令做离线自检：

```powershell
python scripts\verify_cache.py
```

该命令会在自检命名空间中验证缓存“首次未命中、写入后命中、清理后未命中”，不会清理真实业务缓存命名空间。

ASR 兜底环境可用以下命令做离线自检：

```powershell
python scripts\verify_asr.py
```

该命令只检查 `yt-dlp`、`faster-whisper` 是否可导入，以及 `ASR_MODEL`、`ASR_COMPUTE_TYPE`、`ASR_DEVICE` 的实际取值，不会下载 Whisper 模型或音视频文件。默认 `ASR_DEVICE=cpu`，避免无 CUDA 环境误触发 GPU 依赖。

Streamlit UI 可用以下命令做 headless 自检：

```powershell
python scripts\verify_streamlit_ui.py
```

该命令会启动 `app.py`，轮询本地 HTTP 入口，并在返回 `200` 后自动终止服务。它不需要手工打开浏览器，但能证明 UI 入口在本机可启动。

## 正式终验复跑

正式提交前，先确认 `.env` 中已填入真实 Key，并按需设置代理，然后运行：

```powershell
python scripts\preflight_check.py
```

`preflight_check.py` 会检查 `.env`、`YOUTUBE_API_KEY`、`OPENAI_API_KEY`、OpenAI Base URL/模型、ASR 参数、代理和抖音参考 JSON 状态。输出只显示状态和长度，不会打印真实密钥。
普通模式下，缺少 `.env` 或必需 Key 会失败；代理、ASR 默认值等按需配置会显示为 `WARN`，不阻断可直连环境的终验复跑。

填好真实 Key 后，也可以先预览完整终验复跑命令：

```powershell
python scripts\run_final_acceptance.py --dry-run
```

确认无误后运行：

```powershell
python scripts\run_final_acceptance.py --enable-asr
```

该脚本会依次执行前置检查、B 站 + YouTube 30 条真实运行、提交样例刷新、严格自检、审计报告刷新、演示视频生成和提交包生成；任一步失败都会停止，避免把未达标结果覆盖为提交样例。

```powershell
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
```

期望结果：

- `results/PCA_主成分分析.csv`、`results/PCA_主成分分析.json`、`results/PCA_主成分分析.md` 和 `results/PCA_主成分分析_run.log` 同步生成。
- `*_run.log` 中 `total_records` 目标为 30，`evaluation_success_count` 目标不少于 27。
- 若 YouTube 网络出口、B 站字幕或平台风控导致字幕成功率不足，需要保留日志，并在反思报告或验收状态表中说明降级原因。

确认完整结果达标后，刷新最终提交样例：

```powershell
python scripts\refresh_submission_samples.py
```

该脚本会先检查 `results/PCA_主成分分析_run.log`，确认 `total_records >= 30`、评估成功率不低于 90%、CSV 字段完整、CSV 数据行数不低于 run log 中的 `total_records` 且结果同时包含 `bilibili` 与 `youtube`，确认 JSON 为合法列表且记录数不低于 run log 中的 `total_records`，并确认 Markdown 包含运行摘要、推荐学习路径和四个分层，再把 CSV、JSON、Markdown 和 run log 同步到 `输出样例/`。离线自检也会检查 `输出样例/pca_主成分分析.json` 是否为合法非空 JSON 列表。如果结果不达标，脚本会直接失败，避免把半成品覆盖为提交样例。

如需生成终验提交压缩包，可运行：

```powershell
python scripts\package_submission.py
```

该脚本会生成 `提交包/视频学习资源智能筛选系统_终验提交包.zip`，包含源码、README、文档、评估表、答辩材料和输出样例，并排除 `.env`、`.venv/`、`results/`、缓存、`__pycache__/` 等本地私有或运行产物。
如果 README、goal、源码、脚本、测试、文档、评估表、答辩材料或输出样例等必需路径缺失，脚本会直接失败，避免生成不完整提交包。

最终提交前可运行严格模式：

```powershell
python scripts\acceptance_check.py --strict
```

严格模式会把 `.env`、正式演示录屏和双平台完整输出这些人工/外部依赖项也视为失败，适合提交前最后一轮确认。

如需生成面向终验老师的汇总审计报告，可运行：

```powershell
python scripts\final_audit.py
```

该脚本会读取 `acceptance_check.py` 的结果，并写入 `文档/终验审计报告.md`，集中列出通过项、待补齐项和当前结论。

如需重新生成答辩演示说明视频，可运行：

```powershell
python scripts\generate_demo_recording.py
```

该脚本会调用本机 `ffmpeg` 生成 `答辩/演示录屏.mp4`。视频用于说明当前已验证能力和仍需真实 Key 复跑的边界，不会伪造 YouTube 或 LLM 的外部 API 运行结果。

## 输出文件

程序运行后会在 `results/` 目录生成：

- `*.csv`：面向筛选和人工复核的结果表。
- `*.json`：完整结构化结果。
- `*.md`：按入门理解层、数学推导层、代码实操层、应用案例层整理的推荐清单。
- `*_run.log`：单次运行统计。
- `runtime.log`：运行过程日志。
- `cache/`：本地缓存。

## 测试与检查

```powershell
python -m py_compile main.py src\asr_whisper.py src\cache_utils.py src\evaluate.py src\exporters.py src\logging_utils.py src\schema.py src\search_bilibili.py src\search_douyin.py src\search_youtube.py
python -m pytest
python -m ruff check .
python -m black --check .
python scripts\verify_asr.py
python scripts\verify_cache.py
python scripts\verify_streamlit_ui.py
python scripts\preflight_check.py
python scripts\acceptance_check.py
python scripts\final_audit.py
python scripts\generate_demo_recording.py --help
python scripts\run_final_acceptance.py --dry-run
python scripts\refresh_submission_samples.py --help
python scripts\package_submission.py --help
python scripts\generate_pptx.py
```

当前验证记录见 `文档/终验运行记录.md`。

## 注意事项

- 不要提交 `.env`、真实 API Key、Token、Cookie 或账号密码。
- YouTube 搜索依赖 API quota，调试时建议使用缓存。
- 大模型评估会消耗调用额度，建议先小样本测试。
- ASR 首次运行可能需要下载 Whisper 模型，建议先用 `--max 5` 验证。
- 外部平台请求应控制频率，避免触发风控或造成不必要压力。
