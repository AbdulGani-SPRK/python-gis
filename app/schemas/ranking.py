from pydantic import BaseModel, Field


class ScoreExplanation(BaseModel):
    total_score: float = 0.0
    factors: dict[str, float] = Field(default_factory=dict)
