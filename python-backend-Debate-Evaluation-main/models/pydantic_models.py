from pydantic import BaseModel, Field
from typing import List, Optional

class EvaluationResponse(BaseModel):
    # statement: str = Field(..., description="The user's debate statement")
    topic: str = Field(..., description="The debate topic")
    factual_accuracy: float = Field(..., ge=0, le=100, description="Factual accuracy score (0-100%)")
    relevance_score: float = Field(..., ge=0, le=100, description="Relevance to topic score (0-100%)")
    explanation: Optional[str] = Field(None, description="Explanation of the evaluation")
    confidence: float = Field(..., ge=0, le=1, description="Model's confidence in the evaluation")
    sources: List[str] = Field([], description="List of source URLs or references used for evaluation")


class ExchangeScoreResponse(BaseModel):
    topic: str = Field(..., description="The debate topic")
    for_points: float = Field(..., ge=0, le=10, description="Points awarded to the FOR debater (0-10)")
    against_points: float = Field(..., ge=0, le=10, description="Points awarded to the AGAINST debater (0-10)")
    exchange_winner: str = Field(..., description="Who won this exchange: 'for', 'against', or 'tie'")
    reasoning: str = Field(..., description="Explanation of why these points were awarded")
