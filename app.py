from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from main import build_summary, export_results, gather_records
from src.evaluate import evaluate_records
from src.env_utils import is_real_env_value
from src.exporters import build_csv_rows
from src.schema import SearchSummary, VideoRecord

LEARNING_LAYER_NAMES = ("入门理解层", "数学推导层", "代码实操层", "应用案例层")


def _set_env_if_value(name: str, value: str) -> None:
    value = value.strip()
    if is_real_env_value(value):
        os.environ[name] = value


def _configure_proxy(proxy_port: str) -> None:
    proxy_port = proxy_port.strip()
    if not proxy_port:
        return
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["ALL_PROXY"] = proxy_url


async def _run_pipeline(
    *,
    topic: str,
    platforms: list[str],
    max_results: int,
    subtitle_limit: int,
    skip_evaluate: bool,
    enable_asr: bool,
    use_cache: bool,
) -> tuple[pd.DataFrame, dict[str, Path], SearchSummary, list[VideoRecord]]:
    records, errors = await gather_records(
        topic=topic,
        platforms=platforms,
        max_results=max_results,
        subtitle_limit=subtitle_limit,
        enable_asr=enable_asr,
        use_cache=use_cache,
    )
    if not skip_evaluate:
        records, evaluation_errors = await evaluate_records(topic, records, use_cache=use_cache)
        errors.extend(evaluation_errors)

    summary = build_summary(records, errors)
    exported = export_results(topic, records, summary)
    return pd.DataFrame(build_csv_rows(records)), exported, summary, records


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "暂无"
    return ", ".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _format_ratio(count: int, ratio: float) -> str:
    return f"{count} / {ratio:.0%}"


def _build_overview_metrics(summary: SearchSummary) -> dict[str, str]:
    return {
        "total_records": str(summary.total_records),
        "subtitle_success": _format_ratio(summary.subtitle_success_count, summary.subtitle_success_ratio),
        "evaluation_success": _format_ratio(summary.evaluation_success_count, summary.evaluation_success_ratio),
        "platform_distribution": _format_counts(summary.platform_counts),
        "subtitle_source_distribution": _format_counts(summary.subtitle_source_counts),
    }


def _sort_records(records: list[VideoRecord]) -> list[VideoRecord]:
    return sorted(
        records,
        key=lambda record: (
            0 if record.recommend == "yes" else 1,
            -(record.relevance or -1),
            -(record.depth or -1),
            -(record.clarity or -1),
            -record.view,
        ),
    )


def _bucket_name(record: VideoRecord) -> str:
    text = f"{record.title} {record.description}".lower()
    if record.has_code or any(
        token in text for token in ("python", "matlab", "sklearn", "numpy", "代码", "实操", "实战")
    ):
        return "代码实操层"
    if record.has_math or (record.depth or 0) >= 7:
        return "数学推导层"
    if any(token in text for token in ("应用", "案例", "实战应用", "降维", "识别")) and (record.depth or 0) >= 5:
        return "应用案例层"
    return "入门理解层"


def _bucket_learning_records(records: list[VideoRecord]) -> dict[str, list[VideoRecord]]:
    buckets = {name: [] for name in LEARNING_LAYER_NAMES}
    display_records = [record for record in records if record.recommend == "yes"] or records
    for record in _sort_records(display_records):
        buckets[_bucket_name(record)].append(record)
    return buckets


def _score_label(record: VideoRecord) -> str:
    relevance = record.relevance if record.relevance is not None else "待评估"
    depth = record.depth if record.depth is not None else "待评估"
    clarity = record.clarity if record.clarity is not None else "待评估"
    return f"相关性 {relevance} / 深度 {depth} / 清晰度 {clarity}"


def _duration_label(seconds: int) -> str:
    if seconds <= 0:
        return "未知时长"
    minutes = seconds // 60
    return "1 分钟内" if minutes < 1 else f"{minutes} 分钟"


def _filter_table(
    table: pd.DataFrame, platforms: list[str], recommend_filter: str, subtitle_filter: str
) -> pd.DataFrame:
    filtered = table.copy()
    if platforms and "platform" in filtered:
        filtered = filtered[filtered["platform"].isin(platforms)]
    if recommend_filter != "全部" and "recommend" in filtered:
        expected = "yes" if recommend_filter == "推荐" else "no"
        filtered = filtered[filtered["recommend"] == expected]
    if subtitle_filter != "全部" and "has_subtitle" in filtered:
        expected = subtitle_filter == "有字幕"
        filtered = filtered[filtered["has_subtitle"] == expected]
    return filtered


def _render_empty_state() -> None:
    st.info("配置任务后点击“开始筛选”，这里会展示真实运行结果。")
    st.subheader("主要功能")
    cols = st.columns(4)
    features = [
        ("多平台检索", "B 站、YouTube、抖音参考 JSON"),
        ("字幕与 ASR", "抓取字幕，可按需启用 Whisper 兜底"),
        ("LLM 评估", "输出相关性、深度、清晰度和推荐理由"),
        ("结果导出", "生成 CSV、JSON、Markdown 和运行日志"),
    ]
    for col, (title, body) in zip(cols, features):
        with col:
            st.markdown(f"**{title}**")
            st.caption(body)


def _render_overview(summary: SearchSummary) -> None:
    metrics = _build_overview_metrics(summary)
    cols = st.columns(4)
    cols[0].metric("候选总数", metrics["total_records"])
    cols[1].metric("字幕成功", metrics["subtitle_success"])
    cols[2].metric("评估成功", metrics["evaluation_success"])
    cols[3].metric("异常数", str(len(summary.errors)))

    detail_cols = st.columns(2)
    detail_cols[0].caption(f"平台分布：{metrics['platform_distribution']}")
    detail_cols[1].caption(f"字幕来源：{metrics['subtitle_source_distribution']}")
    if summary.errors:
        with st.expander("查看异常信息", expanded=False):
            for error in summary.errors[:10]:
                st.warning(error)


def _render_learning_path(records: list[VideoRecord]) -> None:
    st.subheader("推荐学习路径")
    if not records:
        st.info("当前没有可展示的视频结果。")
        return

    buckets = _bucket_learning_records(records)
    tabs = st.tabs([f"{name} ({len(buckets[name])})" for name in LEARNING_LAYER_NAMES])
    for tab, layer_name in zip(tabs, LEARNING_LAYER_NAMES):
        with tab:
            bucket = buckets[layer_name]
            if not bucket:
                st.caption("当前没有归入这一层的视频。")
                continue
            for record in bucket[:5]:
                with st.container(border=True):
                    st.markdown(f"**[{record.title}]({record.url})**")
                    st.caption(
                        " · ".join(
                            [
                                record.platform,
                                record.author or "未知作者",
                                _duration_label(record.duration),
                                _score_label(record),
                            ]
                        )
                    )
                    st.write(record.reason or "暂未生成推荐理由。")


def _render_results_table(table: pd.DataFrame) -> None:
    st.subheader("结果表")
    if table.empty:
        st.info("当前没有表格结果。")
        return

    filter_cols = st.columns(3)
    platform_options = sorted(table["platform"].dropna().unique().tolist()) if "platform" in table else []
    selected_platforms = filter_cols[0].multiselect("平台筛选", platform_options, default=platform_options)
    recommend_filter = filter_cols[1].selectbox("推荐状态", ["全部", "推荐", "不推荐"])
    subtitle_filter = filter_cols[2].selectbox("字幕状态", ["全部", "有字幕", "无字幕"])
    filtered = _filter_table(table, selected_platforms, recommend_filter, subtitle_filter)
    st.dataframe(filtered, use_container_width=True, hide_index=True)


def _render_exports(exported: dict[str, Path]) -> None:
    st.subheader("导出文件")
    for label, path in exported.items():
        st.code(f"{label}: {path}", language="text")

    csv_bytes = exported["csv"].read_bytes()
    md_text = exported["md"].read_text(encoding="utf-8")
    cols = st.columns(2)
    cols[0].download_button("下载 CSV", data=csv_bytes, file_name=exported["csv"].name, mime="text/csv")
    cols[1].download_button("下载 Markdown", data=md_text, file_name=exported["md"].name, mime="text/markdown")


def main() -> None:
    load_dotenv()
    st.set_page_config(page_title="视频学习资源智能筛选系统", layout="wide")
    st.title("视频学习资源智能筛选系统")
    st.caption("输入学习主题，检索多平台视频，评估资源质量，并生成可复核的学习路径与导出文件。")

    with st.sidebar:
        st.header("任务配置")
        topic = st.text_input("学习主题", value="PCA 主成分分析")
        platforms = st.multiselect(
            "检索平台",
            options=["bilibili", "youtube", "douyin"],
            default=["bilibili", "youtube"],
        )
        max_results = st.number_input("候选数量", min_value=1, max_value=100, value=30, step=1)
        subtitle_limit = st.number_input("单条字幕保留字数", min_value=500, max_value=20000, value=6000, step=500)
        skip_evaluate = st.checkbox("跳过 LLM 评估", value=not is_real_env_value(os.getenv("OPENAI_API_KEY")))
        enable_asr = st.checkbox("启用 ASR 兜底", value=False)
        use_cache = st.checkbox("使用本地缓存", value=True)

        st.header("接口配置")
        youtube_api_key = st.text_input("YouTube API Key", value=os.getenv("YOUTUBE_API_KEY", ""), type="password")
        openai_api_key = st.text_input(
            "OpenAI compatible API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
        )
        openai_base_url = st.text_input(
            "OpenAI compatible Base URL",
            value=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        )
        openai_model = st.text_input("模型名", value=os.getenv("OPENAI_MODEL", "deepseek-chat"))
        proxy_port = st.text_input("本地代理端口", value="")
        douyin_search_mode = st.selectbox(
            "抖音搜索模式",
            options=["sample_json", "external_api"],
            index=0 if os.getenv("DOUYIN_SEARCH_MODE", "sample_json") != "external_api" else 1,
            help="external_api 需要先启动 TikTokDownloader Web API；失败时会回退到参考 JSON。",
        )
        douyin_external_api_base = st.text_input(
            "抖音外部 API 地址",
            value=os.getenv("DOUYIN_EXTERNAL_API_BASE", "http://127.0.0.1:5555"),
        )
        douyin_external_api_token = st.text_input(
            "抖音外部 API Token",
            value=os.getenv("DOUYIN_EXTERNAL_API_TOKEN", ""),
            type="password",
        )
        douyin_sample_json = st.text_input(
            "抖音参考 JSON",
            value=os.getenv("DOUYIN_SAMPLE_JSON", "douyinpachong-main/foshan_hot_videos.json"),
        )

    run_requested = st.button("开始筛选", type="primary", use_container_width=True)
    if run_requested:
        if not topic.strip():
            st.error("请先输入学习主题。")
            return
        if not platforms:
            st.error("请至少选择一个平台。")
            return

        _set_env_if_value("YOUTUBE_API_KEY", youtube_api_key)
        _set_env_if_value("OPENAI_API_KEY", openai_api_key)
        _set_env_if_value("OPENAI_BASE_URL", openai_base_url)
        _set_env_if_value("OPENAI_MODEL", openai_model)
        _set_env_if_value("DOUYIN_SEARCH_MODE", douyin_search_mode)
        _set_env_if_value("DOUYIN_EXTERNAL_API_BASE", douyin_external_api_base)
        _set_env_if_value("DOUYIN_EXTERNAL_API_TOKEN", douyin_external_api_token)
        _set_env_if_value("DOUYIN_SAMPLE_JSON", douyin_sample_json)
        _configure_proxy(proxy_port)

        with st.spinner("正在检索和评估，请稍候..."):
            try:
                table, exported, summary, records = asyncio.run(
                    _run_pipeline(
                        topic=topic,
                        platforms=platforms,
                        max_results=int(max_results),
                        subtitle_limit=int(subtitle_limit),
                        skip_evaluate=skip_evaluate,
                        enable_asr=enable_asr,
                        use_cache=use_cache,
                    )
                )
            except Exception as exc:
                st.error("筛选任务运行失败，请检查接口配置、网络代理或平台访问状态。")
                st.exception(exc)
                return

        st.session_state["latest_result"] = {
            "table": table,
            "exported": exported,
            "summary": summary,
            "records": records,
        }
        st.success("筛选完成")

    latest_result = st.session_state.get("latest_result")
    if latest_result is None:
        _render_empty_state()
        return

    _render_overview(latest_result["summary"])
    _render_learning_path(latest_result["records"])
    _render_results_table(latest_result["table"])
    _render_exports(latest_result["exported"])


if __name__ == "__main__":
    main()
