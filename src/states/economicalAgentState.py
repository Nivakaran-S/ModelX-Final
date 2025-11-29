"""
src/states/economicalAgentState.py
Economical Agent State - handles market data, CSE stock monitoring
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class EconomicalAgentState(TypedDict, total=False):
    """
    State for Economical Agent.
    Monitors CSE stock data, market anomalies, economic indicators.
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
    
    # ===== FEED OUTPUT =====
    final_feed: str
    feed_history: Annotated[List[str], operator.add]
    
    # ===== INTEGRATION WITH PARENT GRAPH =====
    domain_insights: List[Dict[str, Any]]