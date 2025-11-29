"""
src/states/politicalAgentState.py
Political Agent State - handles government gazette, parliament minutes
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class PoliticalAgentState(TypedDict, total=False):
    """
    State for Political Agent.
    Monitors regulatory changes, policy updates, government announcements.
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