from uuid import UUID

from pydantic import BaseModel


class AttributionOut(BaseModel):
    run_id: UUID
    responsible_component: str
    component_confidence: float
    failure_step: int | None
    failure_category: str
    category_confidence: float
    severity: float

    model_config = {"from_attributes": True}


class AnalyzeResponse(BaseModel):
    run_id: UUID
    responsible_component: dict
    failure_step: dict
    failure_category: dict
    severity: float
    causal_graph: dict | None = None


class GraphNode(BaseModel):
    id: str
    weight: float


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
