from pydantic import BaseModel, Field, field_validator
import json
import re

class Structure(BaseModel):
    tldr: str = Field(
        default="Summary generation failed",
        description="generate a too long; didn't read summary",
    )
    motivation: str = Field(
        default="Motivation analysis unavailable",
        description="describe the motivation in this paper",
    )
    method: str = Field(
        default="Method extraction failed",
        description="method of this paper",
    )
    result: str = Field(
        default="Result analysis unavailable",
        description="result of this paper",
    )
    conclusion: str = Field(
        default="Conclusion extraction failed",
        description="conclusion of this paper",
    )
    # --- Judgment fields for relevance / quality / reputation ---
    # These default to safe values so a model that occasionally omits a field (as
    # DeepSeek does) degrades gracefully instead of failing the whole batch:
    # a paper missing the judgment is treated as non-relevant and filtered out.
    is_relevant: bool = Field(
        default=False,
        description="Whether this paper's core contribution is to search engines, "
                    "online advertising, recommender systems, or a directly adjacent "
                    "search/ads/recommendation ranking or personalization component"
    )
    is_high_quality: bool = Field(
        default=False,
        description="Whether the method/experiments are technically sound and the "
                    "idea original enough to be worth reading"
    )
    is_known_affiliation: bool = Field(
        default=False,
        description="Whether the supplied author affiliation evidence establishes "
                    "that an author is from a well-known institution or company"
    )
    priority_score: int = Field(
        default=0, ge=0, le=100,
        description="Importance priority 0-100. Higher = more worth reading. "
                    "Reflects relevance, technical quality, and author/institution evidence."
    )
    reason: str = Field(
        default="",
        description="One short sentence justifying the relevance/quality/priority "
                    "decision, in the output language."
    )

    @field_validator(
        "tldr",
        "motivation",
        "method",
        "result",
        "conclusion",
        mode="before",
    )
    @classmethod
    def normalize_text_field(cls, value):
        """Convert model mistakes like false/object fields into readable text."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, tuple)):
            return "\n".join(cls.normalize_text_field(item) for item in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @field_validator(
        "is_relevant",
        "is_high_quality",
        "is_known_affiliation",
        mode="before",
    )
    @classmethod
    def normalize_boolean_field(cls, value):
        """Accept common string booleans returned by imperfect structured output."""
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "是"}
        return value
