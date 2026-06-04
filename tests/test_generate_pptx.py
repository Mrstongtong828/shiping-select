import zipfile

from scripts.generate_pptx import build_pptx, parse_ppt_markdown


def test_parse_ppt_markdown_reads_slide_sections():
    slides = parse_ppt_markdown(__import__("pathlib").Path("答辩/答辩PPT.md"))

    assert len(slides) >= 10
    assert slides[0].title.startswith("第 1 页")
    assert "视频学习资源智能筛选系统" in slides[0].bullets[0]


def test_build_pptx_creates_valid_zip_package(tmp_path):
    slides = parse_ppt_markdown(__import__("pathlib").Path("答辩/答辩PPT.md"))[:2]
    output = tmp_path / "demo.pptx"

    build_pptx(slides, output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "ppt/presentation.xml" in names
        assert "ppt/slides/slide1.xml" in names
        assert "ppt/slides/slide2.xml" in names
