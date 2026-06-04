import subprocess
import sys
import json
from pathlib import Path

import pytest

from scripts.refresh_submission_samples import refresh_submission_samples

ROOT = Path(__file__).resolve().parents[1]
CSV_HEADER = "platform,title,url,author,view,like,has_subtitle,relevance,depth,clarity," "audience,recommend,reason\n"


def _write_complete_artifacts(results_dir: Path, *, platforms: tuple[str, ...] = ("bilibili", "youtube")) -> None:
    results_dir.mkdir()
    rows = [
        f"{platforms[index % len(platforms)]},样例 {index + 1},https://example.com/{index + 1},"
        "作者,100,10,true,8,7,8,本科入门,yes,理由\n"
        for index in range(30)
    ]
    (results_dir / "PCA_主成分分析.csv").write_text(CSV_HEADER + "".join(rows), encoding="utf-8")
    payload = [
        {
            "platform": platforms[index % len(platforms)],
            "title": f"样例 {index + 1}",
            "url": f"https://example.com/{index + 1}",
        }
        for index in range(30)
    ]
    (results_dir / "PCA_主成分分析.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (results_dir / "PCA_主成分分析.md").write_text(
        "\n".join(
            [
                "# PCA 主成分分析 学习资源推荐",
                "",
                "## 运行摘要",
                "- 候选总数：30",
                "",
                "## 推荐学习路径",
                "- 先看入门理解层。",
                "",
                "## 入门理解层",
                "- 样例",
                "",
                "## 数学推导层",
                "- 样例",
                "",
                "## 代码实操层",
                "- 样例",
                "",
                "## 应用案例层",
                "- 样例",
            ]
        ),
        encoding="utf-8",
    )
    (results_dir / "PCA_主成分分析_run.log").write_text(
        "\n".join(
            [
                "topic=PCA 主成分分析",
                "total_records=30",
                "subtitle_success_count=24",
                "subtitle_success_ratio=0.8000",
                "evaluation_success_count=28",
                "evaluation_success_ratio=0.9333",
                "errors=0",
            ]
        ),
        encoding="utf-8",
    )


def test_refresh_submission_samples_copies_valid_final_run(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)

    copied = refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    copied_names = {path.name for path in copied}
    assert copied_names == {
        "pca_主成分分析.csv",
        "pca_主成分分析.json",
        "pca_主成分分析.md",
        "eval_log.txt",
    }
    assert "bilibili" in (samples_dir / "pca_主成分分析.csv").read_text(encoding="utf-8")
    assert "youtube" in (samples_dir / "pca_主成分分析.csv").read_text(encoding="utf-8")
    assert "total_records=30" in (samples_dir / "eval_log.txt").read_text(encoding="utf-8")


def test_refresh_submission_samples_rejects_incomplete_run(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析_run.log").write_text(
        "total_records=12\nevaluation_success_count=10\nevaluation_success_ratio=0.8333\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="total_records"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_single_platform_results(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir, platforms=("bilibili",))

    with pytest.raises(ValueError, match="required platform"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_missing_csv_fields(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析.csv").write_text("platform,title\nbilibili,样例\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV missing required field"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_short_csv_results(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析.csv").write_text(
        CSV_HEADER
        + "bilibili,样例 1,https://example.com/1,作者,100,10,true,8,7,8,本科入门,yes,理由\n"
        + "youtube,样例 2,https://example.com/2,作者,100,10,true,8,7,8,本科入门,yes,理由\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="CSV row count"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_short_json_results(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析.json").write_text(
        json.dumps([{"platform": "bilibili", "title": "样例"}], ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSON record count"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_artifacts_below_logged_total(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析_run.log").write_text(
        "\n".join(
            [
                "topic=PCA 主成分分析",
                "total_records=31",
                "subtitle_success_count=24",
                "subtitle_success_ratio=0.7742",
                "evaluation_success_count=31",
                "evaluation_success_ratio=1.0000",
                "errors=0",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="CSV row count"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_rejects_incomplete_markdown(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析.md").write_text("# PCA 主成分分析 学习资源推荐\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Markdown missing required section"):
        refresh_submission_samples(results_dir=results_dir, samples_dir=samples_dir)

    assert not samples_dir.exists()


def test_refresh_submission_samples_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "scripts/refresh_submission_samples.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Refresh final submission samples" in result.stdout


def test_refresh_submission_samples_cli_reports_incomplete_run_cleanly(tmp_path):
    results_dir = tmp_path / "results"
    samples_dir = tmp_path / "输出样例"
    _write_complete_artifacts(results_dir)
    (results_dir / "PCA_主成分分析_run.log").write_text(
        "total_records=2\nevaluation_success_count=0\nevaluation_success_ratio=0.0000\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/refresh_submission_samples.py",
            "--results-dir",
            str(results_dir),
            "--samples-dir",
            str(samples_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ERROR:" in result.stderr
    assert "total_records=2" in result.stderr
    assert "Traceback" not in result.stderr
    assert not samples_dir.exists()
