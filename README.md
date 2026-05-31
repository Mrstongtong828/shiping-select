# 视频学习资源智能筛选系统资料包

这是一个面向教学场景的视频学习资源筛选项目资料包。主项目位于 `shiping-select-main`，用于从 B 站、YouTube 等平台检索候选视频，抓取元数据和字幕，并通过大模型评估视频是否适合作为学习资源。

## 目录说明

```text
视频筛选工作流/
|- shiping-select-main/                    # 主项目：视频检索、字幕抓取、LLM 评估、结果导出
|- douyinpachong-main/                     # 抖音抓取参考代码，后续可整合进主工作流
|- 使用步骤说明文档.md                     # 给接手同学看的本地配置说明
|- 视频学习资源智能筛选系统_项目实施方案书_v2.docx
```

## 当前已经实现的内容

- B 站视频搜索
- B 站字幕抓取
- YouTube 视频搜索
- YouTube transcript 抓取接口
- 统一视频数据结构
- LLM 结构化评估
- CSV / JSON / Markdown / 日志导出
- 人工对照评估记录
- Prompt 迭代记录

## 本次上传前修改内容

为方便上传 GitHub 和后续同学使用，本次整理做了这些修改：

- 清理真实 API Key，改为占位符
- 默认大模型改为 `deepseek-v4-pro`
- 新增 `使用步骤说明文档.md`
- 补充主项目 README，说明当前功能和后续开发计划
- 将代理端口替换为 `<PROXY_PORT>`
- 清理 `douyinpachong-main` 中的 Coze Token、Workflow ID 和本机路径
- 明确 `douyinpachong-main` 是抖音抓取参考模块，后续需要合理整合进主工作流

## 后续想要实现的功能

1. 参考或合理使用 `douyinpachong-main` 中的抖音抓取代码，把抖音视频抓取功能加入 `shiping-select-main` 的统一视频筛选工作流。
2. 做一个图形界面，减少手动命令和手动改配置文件。

界面参考功能：

- 可以选择筛选哪个网站的视频内容，例如 B 站、YouTube、抖音等
- 支持单一网站筛选，也支持 `all` 从所有可用网站筛选
- 可以配置模型 API，默认使用 DeepSeek 请求网址和 `deepseek-v4-pro`
- 支持用户自行输入 API Key、模型名和请求网址
- 可以配置 YouTube 等网站的 API Key
- 可以配置本地代理端口
- 可以选择视频筛选类型
- 提供关键词输入框，用于输入想要筛选的视频主题
- 后续可加入结果预览、人工复核、导出和任务记录

## 使用方式

第一次使用请先阅读：

1. `使用步骤说明文档.md`
2. `shiping-select-main/README.md`
3. `shiping-select-main/.env.example`

不要把自己的真实 API Key、Token、Cookie 或账号密码提交到 GitHub。
