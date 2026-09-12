from pydantic import BaseModel, Field, field_validator
import re

class Structure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    motivation: str = Field(description="describe the motivation in this paper")
    method: str = Field(description="method of this paper")
    result: str = Field(description="result of this paper")
    conclusion: str = Field(description="conclusion of this paper")
    # --- Judgment fields for relevance / quality / reputation ---
    # These default to safe values so a model that occasionally omits a field (as
    # DeepSeek does) degrades gracefully instead of failing the whole batch:
    # a paper missing the judgment is treated as non-relevant and filtered out.
    is_relevant: bool = Field(
        default=False,
        description="Whether this paper is genuinely about search, recommendation, "
                    "advertising, personalization, ranking, information retrieval, "
                    "or a closely related topic"
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
