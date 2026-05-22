# 视频学习资源智能筛选系统

一个面向教学场景的多平台视频检索与筛选项目。系统输入一个学习主题后，自动从 B 站和 YouTube 检索候选视频，抓取基础元数据与字幕信息，并可调用 OpenAI 兼容的大模型接口对视频教学价值进行结构化评估，最终导出 CSV / JSON / Markdown / 运行日志。

本项目严格按照《视频学习资源智能筛选系统》项目书要求开发，采用“模块化 + 数据流”架构，保证各模块职责单一、便于测试和后续扩展。

补充说明：同级目录中的 `douyinpachong-main` 保存了抖音视频抓取相关代码和功能参考，后续会参考其中的实现，把抖音抓取能力整合进统一的视频筛选工作流。

## 当前实现进度

当前已经完成的模块：

- B 站搜索
- B 站字幕抓取
- YouTube 搜索
- YouTube 字幕抓取
- 统一数据模型
- 主程序调度与结果导出
- LLM 结构化评估
- 基础日志输出

当前主链路已经可以跑通，适合做课程主题的视频资料筛选与评估。`ASR 兜底`、`抖音抓取`、图形界面和更完整的多站点配置，仍在后续规划中。

## 本次整理与上传前修改内容

为方便后续同学接手和安全上传 GitHub，本次整理做了这些修改：

- 清理 `.env` 中的真实 API Key，统一替换为占位符
- 默认 LLM 模型改为 `deepseek-v4-pro`
- 新增 `使用步骤说明文档.md`，说明 API Key、模型、代理端口和运行步骤
- 补充 README，写明当前功能、项目结构和后续开发方向
- 将项目推进记录中的本地代理端口替换为 `<PROXY_PORT>`
- 清理 `douyinpachong-main` 中的 Coze Token、Workflow ID 和本机路径，改为占位符或相对路径
- 明确 `douyinpachong-main` 目前是抖音抓取参考代码，后续需要合理整合进主工作流

## 项目结构

```text
video-finder/
|- .env                     # API Key，不提交到 Git
|- .env.example             # 环境变量模板
|- .gitignore
|- requirements.txt
|- README.md
|- main.py                  # 流水线主入口
|- prompts/
|  |- eval_template.txt     # 评估 Prompt 模板
|- results/                 # 输出目录
|- src/
|  |- __init__.py
|  |- exporters.py          # CSV / JSON / Markdown / 日志导出
|  |- logging_utils.py      # 日志初始化
|  |- schema.py             # 统一数据模型
|  |- search_bilibili.py    # B 站搜索 + 字幕
|  |- search_youtube.py     # YouTube 搜索 + 字幕
|  |- search_douyin.py      # 抖音抓取（选做，占位）
|  |- asr_whisper.py        # ASR 兜底（选做，占位）
|  |- evaluate.py           # LLM 评估引擎
|- tests/
|  |- test_bilibili.py
|  |- test_evaluate.py
```

## 技术路线

本项目当前主线如下：

1. 用户输入主题
2. 多平台并发检索候选视频
3. 抓取视频标题、作者、播放量、点赞数、发布时间等元数据
4. 获取字幕文本
5. 调用 LLM 进行结构化评分（可通过 `--skip-evaluate` 跳过）
6. 统一整理为结构化数据
7. 导出 CSV / JSON / Markdown / 运行日志

当前重点是把“检索 + 字幕 + 评估 + 导出”这条主链跑稳定，再补齐项目书要求的人工对照评估、Prompt 迭代记录和最终答辩材料。

## 依赖环境

- Python 3.11 或以上
- Windows / macOS / Linux

主要依赖：

- `httpx`
- `google-api-python-client`
- `youtube-transcript-api`
- `pydantic`
- `pandas`
- `python-dotenv`

## 安装方式

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制模板文件：

```bash
copy .env.example .env
```

或在 macOS / Linux：

```bash
cp .env.example .env
```

至少需要配置：

- `YOUTUBE_API_KEY`：运行 YouTube 搜索时必需
- `OPENAI_API_KEY`：运行 LLM 评估时必需

示例：

```env
YOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_compatible_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
```

说明：

- 当前阶段 B 站模块不需要单独 API Key
- 如果只验证 B 站检索，可使用 `--platform bilibili --skip-evaluate`，无需配置 `.env`
- 如果运行完整双平台和 LLM 评估，需要同时配置 `YOUTUBE_API_KEY` 和 `OPENAI_API_KEY`

## 运行方式

### 同时检索 B 站和 YouTube

```bash
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
```

### 仅验证 B 站检索，不调用 LLM

```bash
python main.py --topic "PCA 主成分分析" --platform bilibili --max 15 --skip-evaluate
```

### 仅检索 B 站

```bash
python main.py --topic "PCA 主成分分析" --platform bilibili --max 15
```

### 仅检索 YouTube

```bash
python main.py --topic "PCA principal component analysis" --platform youtube --max 15
```

## 当前输出文件

程序运行后会在 `results/` 目录生成：

- `*.csv`：面向后续筛选与人工查看的表格结果
- `*.json`：完整结构化原始结果
- `*.md`：简要 Markdown 摘要
- `*_run.log`：单次运行统计结果
- `runtime.log`：运行过程日志

## 当前数据字段

当前统一数据结构包含：

- `platform`
- `video_id`
- `title`
- `url`
- `author`
- `view`
- `like`
- `duration`
- `publish_time`
- `description`
- `has_subtitle`
- `subtitle_text`
- `subtitle_language`
- `subtitle_source`

为了与项目书后续验收字段对齐，当前还预留了这些评估字段：

- `relevance`
- `depth`
- `clarity`
- `has_math`
- `has_code`
- `audience`
- `recommend`
- `reason`

配置 `OPENAI_API_KEY` 后，这些字段会由 `evaluate.py` 调用 LLM 赋值；未配置时会保留为空。

## 模块说明

### `main.py`

负责：

- 解析命令行参数
- 调度不同平台搜索模块
- 聚合结果
- 生成输出文件


### 近期优化 · 2025 年 5 月 16 日 (`37575ab`)

- **合并遍历**: `build_summary` 中两个 `sum()` 生成器表达式合并为一次 `for` 循环 + 两个计数器，避免对 records 的两次独立迭代
- **简化 `gather_records`**: 平台协程管理从 `list[tuple[str, Awaitable]]` + 手动解包改为 `dict[str, Awaitable]`，配合 `*coros.values()` 和直接按 key 遍历
- **合并 `print` 调用**: 7 行独立 `print()` 合并为一个 f-string + `\n`，清除冗余的 `print` 前缀
- **清理导入**: 移除未使用的 `Iterable` 类型导入

### `src/search_bilibili.py`

负责：

- B 站视频搜索
- 获取视频详情
- 拉取 B 站字幕

### `src/search_youtube.py`

负责：

- YouTube 视频搜索
- 获取视频统计信息
- 拉取 YouTube transcript

### `src/schema.py`

负责：

- 定义统一数据结构
- 保证多平台输出字段一致

### `src/exporters.py`

负责：

- 导出 CSV
- 导出 JSON
- 导出 Markdown
- 导出运行统计日志

### `src/evaluate.py`

负责：

- 读取 `prompts/eval_template.txt`
- 调用 OpenAI 兼容接口
- 使用 JSON 输出约束和 Pydantic 校验评估结果
- 失败时重试并记录错误

## 测试

运行测试：

```bash
python -m pytest
```

当前测试以基础数据结构和 Prompt 文件存在性检查为主，后续会继续补充模块级测试和集成测试。

## 参考项目

本项目开发过程中主要参考了以下 GitHub 项目的思路或底层能力：

- [Nemo2011/bilibili-api](https://github.com/Nemo2011/bilibili-api)
- [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)

说明：

- 本项目参考这些仓库的接口能力和实现思路
- 所有业务组织、统一数据结构和主程序流程均按本项目书自行实现

## 后续开发计划

下一阶段重点做两类事情：

1. 把 `douyinpachong-main` 中的抖音抓取能力参考、整理并整合到 `shiping-select-main`，让视频筛选工作流支持抖音视频进入统一候选池。
2. 做一个更完整的界面，让同学可以直接在界面里配置筛选任务，减少手动改文件的步骤。

界面希望支持的内容包括：

- 选择筛选哪个网站的视频内容，支持单选某个网站，也支持 `all`
- 配置模型，默认接入 `deepseek-v4-pro`，也支持自定义 API、模型名和请求网址
- 配置 YouTube 等网站的 API 接口，输入后自动接入对应服务
- 配置本地代理端口，方便接入科学上网环境
- 选择视频筛选类型
- 输入要筛选的视频关键词
- 预留更多后续扩展项，例如结果预览、人工复核、导出和任务记录

此外还会继续完善：

- `results/*.md`：更接近项目书要求的人话版分层推荐清单
- 人工对照评估表与准确率统计
- Prompt 迭代记录与反思报告
- `asr_whisper.py`：无字幕视频的 ASR 兜底
- 缓存、重试与更细粒度异常处理
- 测试完善与 README 细化

## 注意事项

- 请勿将 `.env` 提交到仓库
- YouTube 搜索依赖 API Key，请注意每日 quota
- LLM 评估依赖 `OPENAI_API_KEY`，可使用 DeepSeek 等 OpenAI 兼容接口
- 当前版本以“先跑通主线”为目标，推荐分层与人工对照材料仍需完善
