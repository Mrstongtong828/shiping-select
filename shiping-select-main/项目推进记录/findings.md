# 项目发现记录

## 2026-05-20

- 主项目位于 `shiping-select-main`。
- 新增的 `douyinpachong-main` 是独立抖音自动化工具集，依赖 DrissionPage + Chrome + 登录态，不能直接作为主项目模块使用。
- 主项目已有 LLM 评估实现，`README.md` 中“LLM 评估占位”的描述滞后。
- `src/search_douyin.py` 仍是占位实现。
- `src/schema.py` 当前平台类型只包含 `bilibili` 和 `youtube`。
- 项目当前没有 `.env` 文件，只有 `.env.example`。
- `python -m pytest` 测试通过，当前 3 个测试全部通过。
- 已生成 B 站 PCA 输出样例，但没有评估结果，因为运行时使用了 `--skip-evaluate`。
- YouTube 搜索最初使用 `google-api-python-client`，在代理环境下出现连接超时；改为 `httpx` 直接调用 YouTube REST API 后可通过 `<PROXY_PORT>` 代理成功搜索。
- `youtube-transcript-api` 当前版本已改为实例方法 `YouTubeTranscriptApi().fetch(...)`，旧的 `YouTubeTranscriptApi.list_transcripts(...)` 不可用。
- 当前网络出口访问 YouTube transcript 页面会触发 `IpBlocked`，因此 YouTube 搜索可用，但 transcript 抓取仍失败。
- B 站搜索在短时间连续请求时可能返回 412 风控错误。
