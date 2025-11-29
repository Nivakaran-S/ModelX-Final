"""
src/states/meteorologicalAgentState.py
Meteorological Agent State - handles weather and disaster alerts
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class MeteorologicalAgentState(TypedDict, total=False):
    """
    State for Meteorological Agent.
    Monitors DMC alerts and weather forecasts.
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
    # Tracks if new alerts appeared since last run
    last_alerts_hash: Optional[int]
    change_detected: bool
    
    # ===== FEED OUTPUT =====
    final_feed: str  # Human-readable bulletin
    feed_history: Annotated[List[str], operator.add]
    
    # ===== INTEGRATION WITH PARENT GRAPH =====
    # CRITICAL: Output formatted for CombinedAgentState
    domain_insights: List[Dict[str, Any]]