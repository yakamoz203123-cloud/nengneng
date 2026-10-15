"""Render one reviewed 9:16 social page without cropping a print page."""

import math
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from layout_design import SOCIAL_CANVAS, SOCIAL_PROFILE, validate_layout_design
from layout_styles import (
    SOCIAL_BAND_RADIUS_PX,
    SOCIAL_CARD_RADIUS_PX,
    SOCIAL_TEXT_PADDING_PX,
    resolve_text_style,
)


def _pixel_box(area, width, height):
    x, y, box_width, box_height = area
    result = (
        round(x * width),
        round(y * height),
        round((x + box_width) * width),
        round((y + box_height) * height),
    )
    if result[0] < 0 or result[1] < 0 or result[2] > width or result[3] > height:
        raise ValueError("社媒元素超出画布")
    return result


def _wrap_text(text, draw, font, width):
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        line = ""
        for character in paragraph:
            candidate = line + character
            if draw.textlength(candidate, font=font) <= width:
                line = candidate
                continue
            if not line:
                raise ValueError("字幕超出文字安全区")
            lines.append(line)
            line = character
        lines.append(line)
    return lines


def render_social_page(page, output_path, profile="social-vertical-9x16") -> Path:
    """Render a separate 1080x1920 PNG/JPEG after deterministic geometry checks."""
    if not isinstance(page, dict):
        raise ValueError("社媒页面必须是对象")
    if profile != SOCIAL_PROFILE:
        raise ValueError("仅支持social-vertical-9x16")

    layout_design = page.get("layout_design")
    errors = validate_layout_design(layout_design, require_complete=True)
    if errors:
        raise ValueError("; ".join(errors))
    social_layout = layout_design["social_layout"]
    if social_layout["profile"] != profile:
        raise ValueError("社媒profile与layout_design不一致")

    output_path = Path(output_path)
    if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("社媒输出必须是PNG或JPEG")
    if output_path.exists():
        raise FileExistsError(output_path)

    image_value = page.get("image_path")
    if not image_value:
        raise ValueError("社媒页面缺少image_path")
    image_path = Path(image_value)
    if not image_path.is_file():
        raise ValueError("社媒源图不存在")

    width = SOCIAL_CANVAS["width_px"]
    height = SOCIAL_CANVAS["height_px"]
    with Image.open(image_path) as source:
        source.load()
        if source.width * 16 != source.height * 9:
            raise ValueError("社媒源图必须是9:16，不能默认中心裁切印刷页")
        rendered = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

    text = page.get("text", "")
    if not isinstance(text, str):
        raise ValueError("社媒正文必须是字符串")
    text = text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    style = resolve_text_style(layout_design)
    text_box = _pixel_box(social_layout["text_safe_area"], width, height)
    draw = ImageDraw.Draw(rendered)

    font_size = page.get("social_font_size", 54)
    if type(font_size) not in (int, float) or not math.isfinite(font_size) or font_size <= 0:
        raise ValueError("社媒字号必须是正数")
    font_value = page.get("font_path")
    font_path = Path(font_value) if font_value else Path(__file__).resolve().parents[1] / "assets" / "kidsbook-print.ttf"
    if not font_path.is_file():
        raise ValueError("社媒字体路径不可用")
    font = ImageFont.truetype(str(font_path), round(font_size))

    padding = SOCIAL_TEXT_PADDING_PX if style.draws_panel else 0
    content_width = text_box[2] - text_box[0] - 2 * padding
    content_height = text_box[3] - text_box[1] - 2 * padding
    if content_width <= 0 or content_height <= 0:
        raise ValueError("字幕超出文字安全区")
    lines = _wrap_text(text, draw, font, content_width) if text else []
    if len(lines) > layout_design["max_lines"]:
        raise ValueError("社媒字幕超过layout_design.max_lines")
    ascent, descent = font.getmetrics()
    leading = max(round(font_size * 1.25), ascent + descent)
    text_height = (len(lines) - 1) * leading + ascent + descent if lines else 0
    if text_height > content_height:
        raise ValueError("字幕超出文字安全区")

    if style.draws_panel:
        radius = SOCIAL_CARD_RADIUS_PX if style.mode == "soft-card" else SOCIAL_BAND_RADIUS_PX
        draw.rounded_rectangle(text_box, radius=radius, fill=style.panel_rgb)
    x = text_box[0] + padding
    y = text_box[1] + padding
    for index, line in enumerate(lines):
        if style.text_align == "center":
            line_width = draw.textlength(line, font=font)
            line_x = x + (content_width - line_width) / 2
        else:
            line_x = x
        draw.text((line_x, y + index * leading), line, font=font, fill=style.text_rgb)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary = tempfile.mkstemp(suffix=output_path.suffix, dir=output_path.parent)
    os.close(file_descriptor)
    try:
        save_options = {"quality": 95} if output_path.suffix.lower() in {".jpg", ".jpeg"} else {}
        rendered.save(temporary, **save_options)
        os.link(temporary, output_path)
    finally:
        rendered.close()
        if os.path.exists(temporary):
            os.unlink(temporary)
    return output_path
