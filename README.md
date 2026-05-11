# 视频学习资源智能筛选系统

一个面向教学场景的多平台视频检索与筛选项目。系统输入一个学习主题后，自动从 B 站和 YouTube 检索候选视频，抓取基础元数据与字幕信息，并为后续的大模型评估、学习路径整理和结果导出提供统一数据结构。

本项目严格按照《视频学习资源智能筛选系统》项目书要求开发，采用“模块化 + 数据流”架构，保证各模块职责单一、便于测试和后续扩展。

## 当前实现进度

当前已经完成的模块：

- B 站搜索
- B 站字幕抓取
- YouTube 搜索
- YouTube 字幕抓取
- 统一数据模型
- 主程序调度与结果导出
- 基础日志输出

当前为第一阶段版本，`LLM 评估`、`ASR 兜底`、`抖音抓取` 仍保留接口占位，后续继续迭代。

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
|  |- evaluate.py           # LLM 评估引擎（占位）
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
5. 统一整理为结构化数据
6. 导出 CSV / JSON / Markdown / 运行日志

当前重点是先把“检索 + 字幕”这条主链做稳，再接入第二阶段的评估模块。

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

- `YOUTUBE_API_KEY`

示例：

```env
YOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_compatible_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

说明：

- 当前阶段 B 站模块不需要单独 API Key
- 后续接入 `evaluate.py` 时需要 `OPENAI_API_KEY`

## 运行方式

### 同时检索 B 站和 YouTube

```bash
python main.py --topic "PCA 主成分分析" --platform bilibili,youtube --max 30
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
- `audience`
- `recommend`
- `reason`

这些字段会在后续接入 `evaluate.py` 后真正赋值。

## 模块说明

### `main.py`

负责：

- 解析命令行参数
- 调度不同平台搜索模块
- 聚合结果
- 生成输出文件

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

## 测试

运行测试：

```bash
pytest
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

下一阶段将继续实现：

- `evaluate.py`：基于字幕与元数据的大模型结构化评估
- `results/*.md`：更接近项目书要求的人话版推荐清单
- `asr_whisper.py`：无字幕视频的 ASR 兜底
- 缓存、重试与更细粒度异常处理
- 测试完善与 README 细化

## 注意事项

- 请勿将 `.env` 提交到仓库
- YouTube 搜索依赖 API Key，请注意每日 quota
- 当前版本以“先跑通主线”为目标，推荐排序逻辑尚未接入

