from __future__ import annotations
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.states.combinedAgentState import CombinedAgentState

# Configure logging
logger = logging.getLogger("combined_node")

class CombinedAgentNode:
    """
    Implementation of the orchestration nodes for the Mother Graph.
    Includes full aggregation, deduplication, and ranking logic.
    """
    def __init__(self, llm):
        self.llm = llm

    # --- Graph Initiator ------------------------------------------------
    def graph_initiator(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Initialization step executed at START in the graph.
        Responsibilities:
          - update run_count / last_run_ts in state
        """
        logger.info("[GraphInitiator] starting graph iteration")
        
        # Handle state access safely
        current_run = 0
        if state:
            current_run = getattr(state, "run_count", 0)
            
        new_run_count = current_run + 1
        logger.info(f"[GraphInitiator] run_count={new_run_count}")

        return {
            "status": "initiated", 
            "run_count": new_run_count, 
            "last_run_ts": datetime.utcnow()
        }

    # --- Feed Aggregator ------------------------------------------------
    def feed_aggregator_agent(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Aggregates outputs from domain agents.
        - flatten domain insights
        - deduplicate (naive by summary text)
        - simple ranking by risk_score + severity
        - convert to final feed format
        """
        logger.info("[FeedAggregatorAgent] running aggregation")
        
        # 1. Gather inputs
        incoming = []
        if state and state.domain_insights:
            incoming = state.domain_insights
        elif "domain_insights" in kwargs:
            incoming = kwargs["domain_insights"]

        # 2. Flatten if nested lists
        flattened = []
        for item in incoming:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)

        logger.info(f"[FeedAggregatorAgent] received {len(flattened)} raw insights")

        # 3. Naive dedupe by summary prefix
        # (Restored Logic)
        seen = set()
        unique = []
        for ins in flattened:
            # Handle both dict access and object access if Pydantic
            if isinstance(ins, dict):
                summary = str(ins.get("summary", "")).strip()
            else:
                summary = str(getattr(ins, "summary", "")).strip()
                
            key = summary[:120]
            if key not in seen:
                seen.add(key)
                unique.append(ins)

        # 4. Ranking: use risk_score (0..1) and severity boost
        # (Restored Logic)
        severity_boost_map = {"low": 0.0, "medium": 0.05, "high": 0.15, "critical": 0.3}
        
        def score(item):
            # Extract fields safely whether dict or object
            if isinstance(item, dict):
                base = float(item.get("risk_score", 0.0))
                sev = str(item.get("severity", "low"))
            else:
                base = float(getattr(item, "risk_score", 0.0))
                sev = str(getattr(item, "severity", "low"))
                
            return base + severity_boost_map.get(sev, 0.0)

        ranked = sorted(unique, key=score, reverse=True)

        # 5. Convert top-N into Final Feed format
        converted = []
        for ins in ranked:
            # Extract fields
            if isinstance(ins, dict):
                s_id = ins.get("source_event_id")
                summary = ins.get("summary", "")
                domain = ins.get("domain", "unknown")
                r_score = ins.get("risk_score", 0.0)
            else:
                s_id = getattr(ins, "source_event_id", None)
                summary = getattr(ins, "summary", "")
                domain = getattr(ins, "domain", "unknown")
                r_score = getattr(ins, "risk_score", 0.0)

            event_id = s_id or str(uuid.uuid4())
            
            classified = {
                "event_id": event_id,
                "content_summary": summary[:1000],
                "target_agent": domain,
                "confidence_score": round(float(r_score), 3),
            }
            converted.append(classified)

        logger.info(f"[FeedAggregatorAgent] produced {len(converted)} classified events (ranked)")
        return {"final_ranked_feed": converted}

    # --- Data Refresher -------------------------------------------------
    def data_refresher_agent(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Update dashboards, produce snapshots.
        """
        logger.info("[DataRefresherAgent] refreshing aggregated data")
        
        feed = state.final_ranked_feed if state else []

        if not feed:
            logger.info("[DataRefresherAgent] no feed to refresh")
            return {
                "risk_dashboard_snapshot": {
                    "logistics_friction": 0.0,
                    "compliance_volatility": 0.0,
                    "market_instability": 0.0
                }
            }

        # compute simple metrics
        confidences = [float(item.get("confidence_score", 0.0)) for item in feed]
        avg_conf = sum(confidences) / max(1, len(confidences))
        high_count = sum(1 for c in confidences if c >= 0.7)

        # Heuristic mapping -> risk_snapshot
        # (Restored Logic mapping to your RiskMetrics model structure)
        snapshot = {
            "logistics_friction": round(avg_conf, 2), # Example mapping
            "compliance_volatility": round(high_count * 0.1, 2), # Example mapping
            "market_instability": round(avg_conf * 1.2, 2) # Example mapping
        }

        logger.info(f"[DataRefresherAgent] snapshot updated")
        return {"risk_dashboard_snapshot": snapshot}

    # --- Data Refresh Router -------------------------------------------
    def data_refresh_router(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Routing decision after data refresher.
        """
        logger.info("[DataRefreshRouter] making routing decision")
        
        run_count = getattr(state, "run_count", 0)
        max_runs = getattr(state, "max_runs", 5)
        feed = getattr(state, "final_ranked_feed", [])

        if not feed:
            logger.info("[DataRefreshRouter] empty final feed -> ending")
            return {"route": "END"}

        top_conf = max(float(item.get("confidence_score", 0.0)) for item in feed)
        logger.info(f"[DataRefreshRouter] top_confidence={top_conf}")

        # Decision thresholds
        # (Restored Logic: > 0.85 confidence AND run_count < max)
        if top_conf >= 0.85 and run_count < max_runs:
            logger.info("[DataRefreshRouter] threshold met, looping back to GraphInitiator")
            return {"route": "GraphInitiator"}
        else:
            logger.info("[DataRefreshRouter] no loop condition met, routing to END")
            return {"route": "END"}