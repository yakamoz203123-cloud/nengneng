"""Validate layout contract data without claiming to prove visual aesthetics."""

import math


LAYOUT_STYLE_VERSION = "layout-v1"
LAYOUT_MODE_TO_TREATMENT = {
    "scene-integrated": "natural-space",
    "soft-card": "soft-card",
    "narrative-band": "narrative-band",
}
TEXT_ANCHORS = {
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "left",
    "right",
    "center",
}
TEXT_ALIGNS = {"left", "center"}
PAGE_RHYTHMS = {"establishing", "action", "pause", "turn", "resolution"}
PALETTE_TOKENS = {"warm-paper", "cool-sky", "soft-leaf"}
STATUSES = {"pending", "passed", "failed"}
SOCIAL_PROFILE = "social-vertical-9x16"
SOCIAL_CANVAS = {"width_px": 1080, "height_px": 1920}
SOCIAL_SOURCE_ASPECT_RATIO = "9:16"
REVIEW_RELATIONSHIPS = {"integrated", "soft-card", "narrative-band"}
REVIEW_CONTRASTS = {"passed", "failed"}
GENERIC_FOCAL_POINTS = {
    "主体",
    "焦点",
    "人物",
    "角色",
    "主角",
    "subject",
    "focal point",
    "main subject",
}
GENERIC_SAFE_AREAS = {
    "安全区",
    "文字安全区",
    "留白",
    "空白",
    "safe area",
    "text safe area",
}
GENERIC_REVIEW_EVIDENCE = {
    "已检查",
    "已审核",
    "效果良好",
    "通过",
    "已通过",
    "检查通过",
    "审核通过",
    "ok",
    "okay",
    "已检查效果良好",
}


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _specific_text(value, generic_values):
    return _nonempty(value) and value.strip().casefold() not in generic_values


def _evidence_key(value):
    return "".join(character for character in value.casefold() if character.isalnum())


def _require_field(value, key, errors, label=None):
    if key not in value:
        errors.append(f"缺少{label or key}")


def _validate_normalized_area(value, field, errors):
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(_finite_number(item) for item in value)
    ):
        errors.append(f"{field}必须是四个归一化数值")
        return
    x, y, width, height = value
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        errors.append(f"{field}必须位于归一化画布范围内")


def _validate_social_layout(value, require_complete, errors):
    if value is None:
        if require_complete:
            errors.append("完成模式需要social_layout")
        return
    if not isinstance(value, dict):
        errors.append("social_layout必须是对象")
        return

    required = (
        "profile",
        "canvas",
        "subject_safe_area",
        "text_safe_area",
        "avoid_regions",
        "source_aspect_ratio",
        "status",
    )
    if require_complete:
        for field in required:
            _require_field(value, field, errors, f"social_layout.{field}")

    if "profile" in value and value["profile"] != SOCIAL_PROFILE:
        errors.append("social_layout.profile必须是social-vertical-9x16")
    if "canvas" in value and value["canvas"] != SOCIAL_CANVAS:
        errors.append("social_layout.canvas必须是1080×1920")
    for field in ("subject_safe_area", "text_safe_area"):
        if field in value:
            _validate_normalized_area(value[field], f"social_layout.{field}", errors)
    if "avoid_regions" in value and (
        not isinstance(value["avoid_regions"], list)
        or not all(_nonempty(item) for item in value["avoid_regions"])
    ):
        errors.append("social_layout.avoid_regions必须是非空字符串列表")
    if (
        "source_aspect_ratio" in value
        and value["source_aspect_ratio"] != SOCIAL_SOURCE_ASPECT_RATIO
    ):
        errors.append("social_layout.source_aspect_ratio必须是9:16")
    if "status" in value and value["status"] not in STATUSES:
        errors.append("social_layout.status必须是pending、passed或failed")
    elif require_complete and value.get("status") != "passed":
        errors.append("完成模式要求social_layout.status为passed")


def validate_layout_design(
    value: dict | None, require_complete: bool = False
) -> list[str]:
    """Return stable Chinese contract errors for one page's layout design."""
    if value is None:
        return ["完成模式需要layout_design"] if require_complete else []
    if not isinstance(value, dict):
        return ["layout_design必须是对象"]

    errors = []
    required = (
        "layout_style_version",
        "layout_mode",
        "text_anchor",
        "text_treatment",
        "text_align",
        "max_lines",
        "focal_point",
        "text_safe_area",
        "avoid_covering",
        "page_rhythm",
        "palette_token",
        "status",
        "social_layout",
    )
    if require_complete:
        for field in required:
            _require_field(value, field, errors)

    if (
        "layout_style_version" in value
        and value["layout_style_version"] != LAYOUT_STYLE_VERSION
    ):
        errors.append("layout_style_version必须是layout-v1")
    if "layout_mode" in value and value["layout_mode"] not in LAYOUT_MODE_TO_TREATMENT:
        errors.append("layout_mode必须是受支持的版式模式")
    if "text_anchor" in value and value["text_anchor"] not in TEXT_ANCHORS:
        errors.append("text_anchor必须是受支持的文字锚点")
    if "text_treatment" in value:
        if value["text_treatment"] not in set(LAYOUT_MODE_TO_TREATMENT.values()):
            errors.append("text_treatment必须是受支持的文字处理方式")
        elif (
            value.get("layout_mode") in LAYOUT_MODE_TO_TREATMENT
            and value["text_treatment"]
            != LAYOUT_MODE_TO_TREATMENT[value["layout_mode"]]
        ):
            errors.append("layout_mode与text_treatment必须匹配")
    if "text_align" in value and value["text_align"] not in TEXT_ALIGNS:
        errors.append("text_align必须是left或center")
    if "max_lines" in value and (
        type(value["max_lines"]) is not int or value["max_lines"] <= 0
    ):
        errors.append("max_lines必须是正整数")
    if "focal_point" in value and not _specific_text(
        value["focal_point"], GENERIC_FOCAL_POINTS
    ):
        errors.append("focal_point必须描述具体画面对象或动作")
    if "text_safe_area" in value and not _specific_text(
        value["text_safe_area"], GENERIC_SAFE_AREAS
    ):
        errors.append("text_safe_area必须描述实际画面文字区域")
    if "avoid_covering" in value and (
        not isinstance(value["avoid_covering"], list)
        or not all(_nonempty(item) for item in value["avoid_covering"])
    ):
        errors.append("avoid_covering必须是非空字符串列表")
    if "page_rhythm" in value and value["page_rhythm"] not in PAGE_RHYTHMS:
        errors.append("page_rhythm必须是受支持的页面节奏")
    if "palette_token" in value and value["palette_token"] not in PALETTE_TOKENS:
        errors.append("palette_token必须是受支持的调色板令牌")
    if "status" in value and value["status"] not in STATUSES:
        errors.append("status必须是pending、passed或failed")
    elif require_complete and value.get("status") != "passed":
        errors.append("完成模式要求layout_design.status为passed")

    _validate_social_layout(value.get("social_layout"), require_complete, errors)
    return errors


def validate_layout_review(
    value: dict | None, require_complete: bool = False
) -> list[str]:
    """Return stable Chinese contract errors for one page's human layout review."""
    if value is None:
        return ["完成模式需要layout_review"] if require_complete else []
    if not isinstance(value, dict):
        return ["layout_review必须是对象"]

    errors = []
    required = (
        "status",
        "evidence",
        "text_image_relationship",
        "contrast",
        "focal_point_clear",
        "occlusion",
        "rhythm_reason",
    )
    if require_complete:
        for field in required:
            _require_field(value, field, errors, f"layout_review.{field}")

    if "status" in value and value["status"] not in STATUSES:
        errors.append("layout_review.status必须是pending、passed或failed")
    elif require_complete and value.get("status") != "passed":
        errors.append("完成模式要求layout_review.status为passed")
    if "evidence" in value and (
        not _nonempty(value["evidence"])
        or _evidence_key(value["evidence"]) in GENERIC_REVIEW_EVIDENCE
    ):
        errors.append("layout_review.evidence必须提供具体版式证据")
    if (
        "text_image_relationship" in value
        and value["text_image_relationship"] not in REVIEW_RELATIONSHIPS
    ):
        errors.append("layout_review.text_image_relationship必须是受支持的关系类型")
    if "contrast" in value and value["contrast"] not in REVIEW_CONTRASTS:
        errors.append("layout_review.contrast必须是passed或failed")
    elif require_complete and value.get("contrast") != "passed":
        errors.append("完成模式要求layout_review.contrast为passed")
    if "focal_point_clear" in value and type(value["focal_point_clear"]) is not bool:
        errors.append("layout_review.focal_point_clear必须是布尔值")
    elif require_complete and value.get("focal_point_clear") is not True:
        errors.append("完成模式要求layout_review.focal_point_clear为true")
    if "occlusion" in value and not _nonempty(value["occlusion"]):
        errors.append("layout_review.occlusion必须是非空字符串")
    elif require_complete and value.get("occlusion") != "none":
        errors.append("完成模式要求layout_review.occlusion为none")
    if "rhythm_reason" in value and not _nonempty(value["rhythm_reason"]):
        errors.append("layout_review.rhythm_reason必须是非空字符串")
    return errors
