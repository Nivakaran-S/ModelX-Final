"""
src/states/intelligenceAgentState.py
Intelligence Agent State - Competitive Intelligence & Profile Monitoring
"""
import operator 
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict, Annotated


class IntelligenceAgentState(TypedDict, total=False):
    """
    State for Intelligence Agent.
    Monitors competitors, profiles, product reviews, competitive intelligence.
    """
    
    # ===== ORCHESTRATOR/WORKER BOOKKEEPING =====
    generated_tasks: List[Dict[str, Any]]
    current_task: Optional[Dict[str, Any]]
    tasks_for_workers: List[Dict[str, Any]]
    worker: Optional[List[Dict[str, Any]]]
    
    # ===== TOOL RESULTS =====
    worker_results: Annotated[List[Dict[str, Any]], operator.add]
    latest_worker_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # ===== CHANGE DETECTION =====
    last_alerts_hash: Optional[int]
    change_detected: bool
    
    # ===== SOCIAL MEDIA MONITORING =====
    social_media_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # ===== STRUCTURED FEED OUTPUT =====
    profile_feeds: Dict[str, List[Dict[str, Any]]]  # {username: [posts]}
    competitor_feeds: Dict[str, List[Dict[str, Any]]]  # {competitor: [mentions]}
    product_review_feeds: Dict[str, List[Dict[str, Any]]]  # {product: [reviews]}
    local_intel: List[Dict[str, Any]]  # Local competitors
    global_intel: List[Dict[str, Any]]  # Global competitors
    
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
