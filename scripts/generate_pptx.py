from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Slide:
    title: str
    bullets: tuple[str, ...]


def parse_ppt_markdown(path: Path) -> list[Slide]:
    """Parse the simple `## page title` + bullet-list draft used by this project."""
    slides: list[Slide] = []
    current_title = ""
    bullets: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current_title:
                slides.append(Slide(current_title, tuple(bullets)))
            current_title = line.removeprefix("## ").strip()
            bullets = []
            continue
        if line.startswith("- "):
            bullets.append(line.removeprefix("- ").strip())
    if current_title:
        slides.append(Slide(current_title, tuple(bullets)))
    return slides


def _relationship_xml(target: str, relationship_type: str, relationship_id: str) -> str:
    return (
        f'<Relationship Id="{relationship_id}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{relationship_type}" '
        f'Target="{target}"/>'
    )


def _content_types(slide_count: int) -> str:
    overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {overrides}
</Types>"""


def _root_rels() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {_relationship_xml("ppt/presentation.xml", "officeDocument", "rId1")}
  {_relationship_xml("docProps/core.xml", "metadata/core-properties", "rId2")}
  {_relationship_xml("docProps/app.xml", "extended-properties", "rId3")}
</Relationships>"""


def _presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, slide_count + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
    {slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def _presentation_rels(slide_count: int) -> str:
    relationships = "\n".join(
        _relationship_xml(f"slides/slide{i}.xml", "slide", f"rId{i}") for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {relationships}
</Relationships>"""


def _text_shape(shape_id: int, x: int, y: int, cx: int, cy: int, font_size: int, lines: list[str]) -> str:
    paragraphs = []
    for line in lines:
        safe = escape(line)
        paragraphs.append(
            f"""<a:p><a:r><a:rPr lang="zh-CN" sz="{font_size}"><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>{safe}</a:t></a:r></a:p>"""
        )
    body = "".join(paragraphs)
    return f"""<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="TextBox {shape_id}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>
  <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{body}</p:txBody>
</p:sp>"""


def _slide_xml(slide: Slide) -> str:
    title = re.sub(r"^第\s*\d+\s*页[：:]\s*", "", slide.title).strip() or slide.title
    bullet_lines = [f"• {bullet}" for bullet in slide.bullets] or ["• 内容待补充"]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F7F3EA"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {_text_shape(2, 650000, 450000, 10800000, 900000, 3800, [title])}
      {_text_shape(3, 900000, 1550000, 10500000, 4600000, 2200, bullet_lines)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def _app_xml(slide_count: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
  <PresentationFormat>宽屏</PresentationFormat>
  <Slides>{slide_count}</Slides>
</Properties>"""


def _core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>视频学习资源智能筛选系统答辩</dc:title>
  <dc:creator>视频学习资源智能筛选系统项目组</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
</cp:coreProperties>"""


def build_pptx(slides: list[Slide], output_path: Path) -> None:
    if not slides:
        raise ValueError("No slides parsed from draft")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(slides)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("docProps/app.xml", _app_xml(len(slides)))
        archive.writestr("docProps/core.xml", _core_xml())
        archive.writestr("ppt/presentation.xml", _presentation_xml(len(slides)))
        archive.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels(len(slides)))
        for index, slide in enumerate(slides, start=1):
            archive.writestr(f"ppt/slides/slide{index}.xml", _slide_xml(slide))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 答辩PPT.pptx from 答辩PPT.md")
    parser.add_argument("--input", default=str(ROOT / "答辩" / "答辩PPT.md"), help="Markdown draft path")
    parser.add_argument("--output", default=str(ROOT / "答辩" / "答辩PPT.pptx"), help="Output PPTX path")
    args = parser.parse_args()

    slides = parse_ppt_markdown(Path(args.input))
    build_pptx(slides, Path(args.output))
    print(f"Generated {args.output} with {len(slides)} slides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
