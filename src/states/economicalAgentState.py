"""
src/states/economicalAgentState.py
Economical Agent State - handles market data, CSE stock monitoring, economic indicators
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class EconomicalAgentState(TypedDict, total=False):
    """
    State for Economical Agent.
    Monitors CSE stock data, market anomalies, economic indicators, financial news.
    """
    
    # ===== ORCHESTRATOR/WORKER BOOKKEEPING =====
    generated_tasks: List[Dict[str, Any]]
    current_task: Optional[Dict[str, Any]]
    tasks_for_workers: List[Dict[str, Any]]
    worker: Optional[List[Dict[str, Any]]]
    
    # ===== TOOL RESULTS =====
    worker_results: Annotated[List[Dict[str, Any]], operator.add]
    latest_worker_results: List[Dict[str, Any]]
    
    # ===== CHANGE DETECTION =====
    last_alerts_hash: Optional[int]
    change_detected: bool
    
    # ===== SOCIAL MEDIA MONITORING =====
    social_media_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # ===== STRUCTURED FEED OUTPUT =====
    market_feeds: Dict[str, List[Dict[str, Any]]]  # {sector: [posts]}
    national_feed: List[Dict[str, Any]]  # Overall Sri Lanka economy
    world_feed: List[Dict[str, Any]]  # Global economy affecting SL
    
    # ===== LLM PROCESSING =====
    llm_summary: Optional[str]
    structured_output: Dict[str, Any]  # Final formatted output
    
    # ===== FEED OUTPUT =====
    final_feed: str
    feed_history: Annotated[List[str], operator.add]
    
    # ===== INTEGRATION WITH PARENT GRAPH =====
    domain_insights: List[Dict[str, Any]]
    
    # ===== FEED AGGREGATOR =====
    aggregator_stats: Dict[str, Any]
    dataset_path: str