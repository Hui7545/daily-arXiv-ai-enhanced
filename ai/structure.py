from pydantic import BaseModel, Field, field_validator
import re

class Structure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    motivation: str = Field(description="describe the motivation in this paper")
    method: str = Field(description="method of this paper")
    result: str = Field(description="result of this paper")
    conclusion: str = Field(description="conclusion of this paper")
    # --- Judgment fields for relevance / quality / reputation ---
    is_recommendation_related: bool = Field(
        description="Whether this paper is genuinely about recommender systems "
                    "(user/item modeling, collaborative filtering, sequential "
                    "recommendation, CTR/ranking, LLM-based recommendation, etc.)"
    )
    is_high_quality: bool = Field(
        description="Whether the method/experiments are technically sound and the "
                    "idea original enough to be worth reading"
    )
    is_known_affiliation: bool = Field(
        description="Whether any author is from a well-known institution or company "
                    "(top universities, big labs, major tech companies)"
    )
    priority_score: int = Field(
        ge=0, le=100,
        description="Importance priority 0-100. Higher = more worth reading. "
                    "Reflects relevance, technical quality, and author/institution fame."
    )
    reason: str = Field(
        description="One short sentence justifying the relevance/quality/priority "
                    "decision, in the output language."
    )