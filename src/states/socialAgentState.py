"""
src/states/socialAgentState.py
Social Agent State - handles trending topics, events, people, social intelligence
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class SocialAgentState(TypedDict, total=False):
    """
    State for Social Agent.
    Monitors trending topics, events, people, social sentiment across geographic scopes.
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
    geographic_feeds: Dict[str, List[Dict[str, Any]]]  # {region: [posts]}
    sri_lanka_feed: List[Dict[str, Any]]  # Sri Lankan trending
    asia_feed: List[Dict[str, Any]]  # Asian trends
    world_feed: List[Dict[str, Any]]  # World trends
    
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