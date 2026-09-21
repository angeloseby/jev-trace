from pydantic import BaseModel


class RecommendationOut(BaseModel):
    recommendation: str
    confidence: float

    # alias for API spec `action`
    model_config = {"populate_by_name": True}


class RecommendationListOut(BaseModel):
    recommendations: list[RecommendationOut]
