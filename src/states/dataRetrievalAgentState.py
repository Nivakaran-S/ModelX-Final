import operator 
from typing_extensions import Optional, Annotated, List, Literal, TypedDict
from typing import Dict, Any, Union
from datetime import datetime
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class ScrapingTask(BaseModel):
    """Instruction from Master Agent to Worker."""
    tool_name: Literal[
        "scrape_linkedin",
        "scrape_instagram",
        "scrape_facebook",
        "scrape_reddit",
        "scrape_twitter",
        "scrape_government_gazette",
        "scrape_parliament_minutes",
        "scrape_train_schedule",
        "scrape_cse_stock_data",
        "scrape_local_news",
    ]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: Literal["high", "normal"] = "normal"


class RawScrapedData(BaseModel):
    """Output from a Worker's tool execution."""
    source_tool: str
    raw_content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: Literal["success", "failed"]


class ClassifiedEvent(BaseModel):
    """Final output after classification."""
    event_id: str
    content_summary: str
    target_agent: str
    confidence_score: float


class DataRetrievalAgentState(BaseModel):
    """State for the Orchestrator-Worker Workflow."""
    messages: Annotated[List[BaseMessage], operator.add] = Field(default_factory=list)
    generated_tasks: List[ScrapingTask] = Field(default_factory=list)
    worker_results: Annotated[List[RawScrapedData], operator.add] = Field(
        default_factory=list
    )
    classified_buffer: Annotated[List[ClassifiedEvent], operator.add] = Field(
        default_factory=list
    )
    previous_tasks: List[str] = Field(default_factory=list)
    current_task: Optional[ScrapingTask] = None
    tasks_for_workers: List[Dict[str, Any]] = Field(default_factory=list)
    worker: Any = None
    latest_worker_results: List[RawScrapedData] = Field(default_factory=list)
    
    # --- Integration with Main Graph ---
    # ADDED: Critical for passing data to the FeedAggregator
    domain_insights: List[Dict[str, Any]] = Field(default_factory=list)