# 终验提交材料说明

本文档用于说明 `文档/`、`评估表/`、`输出样例/` 和 `答辩/` 目录中各材料的用途，便于老师或答辩评委快速定位项目证据。

## 运行基准

当前提交以仓库根目录开发版为准，即从项目根目录运行 `main.py`、`app.py` 和 `scripts/` 下的工具；不以 `shiping-select-main/` 副本作为主运行目录。

根目录 `README.md` 是主要安装和运行说明，包含虚拟环境、API Key、代理、CLI、Streamlit UI、缓存、ASR、抖音参考 JSON 和终验复跑命令。

## 文档目录

- `文档/README.md`：本提交材料说明。
- `文档/验收状态表.md`：逐项记录任务书和 `goal.md` 的完成状态、证据和后续动作。
- `文档/终验运行记录.md`：记录最近一轮本机验证命令、结果和剩余终验动作。
- `文档/终验审计报告.md`：由 `python scripts\final_audit.py` 自动生成，汇总自检通过项、待补齐项和当前结论。
- `文档/反思报告.md`：不少于 1500 字，说明实现过程、问题、取舍和后续改进。
- `文档/Prompt迭代记录.md`：记录 V1/V2/V3 Prompt 迭代和结构化评估字段设计。
- `文档/抖音抓取降级说明与工程代价对比.md`：说明抖音加分项的可运行降级方案、人工登录/风控边界和工程代价。
- `文档/周报/Week01_周报.md` 至 `文档/周报/Week04_周报.md`：记录 4 周项目推进过程。

## 评估表

- `评估表/人工对照评估表.csv`：人工抽样对照数据。
- `评估表/人工对照评估结果.md`：人工与 LLM 评估一致率结论，当前记录为 80%，达到任务书要求的 70%。

## 输出样例

- `输出样例/pca_主成分分析.csv`：CSV 结构化结果样例。
- `输出样例/pca_主成分分析.json`：JSON 结构化结果样例。
- `输出样例/pca_主成分分析.md`：Markdown 推荐清单样例。
- `输出样例/eval_log.txt`：运行统计日志样例。

注意：当前输出样例用于证明导出格式、中文分层和材料结构可用。真实双平台 30 条结果需要在 `.env` 中配置 `YOUTUBE_API_KEY` 和 `OPENAI_API_KEY` 后运行，并通过 `scripts/refresh_submission_samples.py` 刷新。

## 答辩材料

- `答辩/答辩大纲.md`：答辩讲解提纲。
- `答辩/答辩PPT.md`：PPT 文本草稿。
- `答辩/答辩PPT.pptx`：已生成的答辩演示文件。
- `答辩/演示录屏说明.md`：演示视频生成方式、展示内容和真实 API 复跑边界说明。
- `答辩/演示录屏.mp4`：由 `python scripts\generate_demo_recording.py` 生成的终验演示说明视频。

说明：当前 `答辩/演示录屏.mp4` 用于集中展示项目能力、离线自检结果和剩余外部依赖；若老师要求真实浏览器逐步操作录屏，可按 `答辩/演示录屏说明.md` 中的脚本重新录制替换。

## 自检命令

提交前可在项目根目录运行：

```powershell
python scripts\acceptance_check.py
```

如需生成汇总审计报告，可运行：

```powershell
python scripts\final_audit.py
```

如需重新生成演示说明视频，可运行：

```powershell
python scripts\generate_demo_recording.py
```

填好真实 `.env` 后，可预览或执行完整终验复跑编排：

```powershell
python scripts\run_final_acceptance.py --dry-run
python scripts\run_final_acceptance.py --enable-asr
```

严格终验前可运行：

```powershell
python scripts\acceptance_check.py --strict
```

严格模式会把真实 `.env` 和双平台 30 条完整输出视为必须完成项；演示视频已作为答辩材料纳入提交包。

## 提交包

需要把当前材料打包时，可在项目根目录运行：

```powershell
python scripts\package_submission.py
```

脚本会生成 `提交包/视频学习资源智能筛选系统_终验提交包.zip`，包含源码、根目录 `README.md`、`文档/`、`评估表/`、`答辩/` 和 `输出样例/`，并自动排除 `.env`、`.venv/`、`results/`、缓存目录和 `__pycache__/`，避免把真实密钥或本地运行产物放入提交包。

提交包中的 `文档/终验审计报告.md` 可作为答辩前快速说明材料，用于展示哪些离线验收项已通过，哪些仍依赖真实 Key、正式录屏或双平台完整复跑。
