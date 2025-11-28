import operator 
from typing_extensions import Optional, Annotated, List, Literal, TypedDict
from typing import Dict, Any, Union
from datetime import datetime
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ==========================================
# 1. SHARED & FINAL OUTPUT MODELS
# ==========================================

class RiskMetrics(BaseModel):
    """
    Quantifiable indicators for the Operational Risk Radar.
    """
    logistics_friction: float = Field(default=0.0, description="Route risk score")
    compliance_volatility: float = Field(default=0.0, description="Regulatory risk")
    market_instability: float = Field(default=0.0, description="Volatility index")

class DomainInsight(BaseModel):
    """Output from a Domain Agent."""
    source_event_id: str
    domain: Literal["political", "mobility", "market", "weather", "social"]
    severity: Literal["low", "medium", "high", "critical"] 
    summary: str
    risk_score: float = 0.0
    actionable_advice: Optional[str] = None

class ClassifiedEvent(BaseModel):
    """Final output after classification."""
    event_id: str
    content_summary: str
    target_agent: str
    confidence_score: float


class ModelXAgentState(MessagesState):
    """
    Main state for the complete agentic AI system.
    """
    pending_events: List[ClassifiedEvent] = Field(default_factory=list)
    domain_insights: Annotated[List[DomainInsight], operator.add]
    final_ranked_feed: List[Dict] = Field(default_factory=list)
    risk_dashboard_snapshot: RiskMetrics = Field(default_factory=RiskMetrics)
    run_mode: Literal["background_monitor", "user_investigation"] = "background_monitor"