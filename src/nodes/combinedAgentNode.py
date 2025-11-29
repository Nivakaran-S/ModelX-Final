"""
src/nodes/combinedAgentNode.py
COMPLETE IMPLEMENTATION - Orchestration nodes for ModelX Mother Graph
Implements: GraphInitiator, FeedAggregator, DataRefresher, DataRefreshRouter
"""
from __future__ import annotations
import uuid
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("combined_node")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)


class CombinedAgentNode:
    """
    Orchestration nodes for the Mother Graph (CombinedAgentState).
    
    Implements the Fan-In logic after domain agents complete:
    1. GraphInitiator - Starts each iteration & Clears previous state
    2. FeedAggregator - Collects and ranks domain insights
    3. DataRefresher - Updates risk dashboard
    4. DataRefreshRouter - Decides to loop or end
    """
    
    def __init__(self, llm):
        self.llm = llm

    # =========================================================================
    # 1. GRAPH INITIATOR
    # =========================================================================
    
    def graph_initiator(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialization step executed at START in the graph.
        
        Responsibilities:
        - Increment run counter
        - Timestamp the execution
        - CRITICAL: Send "RESET" signal to clear domain_insights from previous loop
        
        Returns:
            Dict updating run_count, last_run_ts, and clearing data lists
        """
        logger.info("[GraphInitiator] ===== STARTING GRAPH ITERATION =====")
        
        current_run = getattr(state, "run_count", 0)
        new_run_count = current_run + 1
        
        logger.info(f"[GraphInitiator] Run count: {new_run_count}")
        logger.info(f"[GraphInitiator] Timestamp: {datetime.utcnow().isoformat()}")
        
        return {
            "run_count": new_run_count,
            "last_run_ts": datetime.utcnow(),
            # CRITICAL FIX: Send "RESET" string to trigger the custom reducer 
            # in CombinedAgentState. This wipes the list clean for the new loop.
            "domain_insights": "RESET",
            "final_ranked_feed": []
        }

    # =========================================================================
    # 2. FEED AGGREGATOR AGENT
    # =========================================================================
    
    def feed_aggregator_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL NODE: Aggregates outputs from all domain agents.
        
        This implements the "Fan-In (Reduce Phase)" from your architecture:
        - Collects domain_insights from all agents
        - Deduplicates similar events
        - Ranks by risk_score + severity
        - Converts to ClassifiedEvent format
        
        Input: domain_insights (List[Dict]) from state
        Output: final_ranked_feed (List[Dict])
        """
        logger.info("[FeedAggregatorAgent] ===== AGGREGATING DOMAIN INSIGHTS =====")
        
        # Step 1: Gather domain insights
        # Note: In the new state model, this will be a List[Dict] gathered from parallel agents
        incoming = getattr(state, "domain_insights", [])
        
        # Handle case where incoming might be the "RESET" string (edge case protection)
        if isinstance(incoming, str):
            incoming = []
        
        if not incoming:
            logger.warning("[FeedAggregatorAgent] No domain insights received!")
            return {"final_ranked_feed": []}
        
        # Step 2: Flatten nested lists
        # Some agents may return [[insight], [insight]] due to reducer logic
        flattened: List[Dict[str, Any]] = []
        for item in incoming:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)
        
        logger.info(f"[FeedAggregatorAgent] Received {len(flattened)} raw insights from domain agents")
        
        # Step 3: Deduplicate by summary text (first 120 chars)
        seen = set()
        unique: List[Dict[str, Any]] = []
        
        for ins in flattened:
            summary = str(ins.get("summary", "")).strip()
            if not summary:
                continue
                
            # Create dedup key from first 120 chars
            key = summary[:120]
            
            if key not in seen:
                seen.add(key)
                unique.append(ins)
        
        logger.info(f"[FeedAggregatorAgent] After deduplication: {len(unique)} unique insights")
        
        # Step 4: Rank by risk_score + severity boost
        severity_boost_map = {
            "low": 0.0,
            "medium": 0.05,
            "high": 0.15,
            "critical": 0.3
        }
        
        def calculate_score(item: Dict[str, Any]) -> float:
            """Calculate composite risk score"""
            base = float(item.get("risk_score", 0.0))
            severity = str(item.get("severity", "low")).lower()
            boost = severity_boost_map.get(severity, 0.0)
            return base + boost
        
        # Sort descending by score
        ranked = sorted(unique, key=calculate_score, reverse=True)
        
        logger.info(f"[FeedAggregatorAgent] Top 3 events by score:")
        for i, ins in enumerate(ranked[:3]):
            score = calculate_score(ins)
            domain = ins.get("domain", "unknown")
            summary_preview = str(ins.get("summary", ""))[:80]
            logger.info(f"  {i+1}. [{domain}] Score={score:.3f} | {summary_preview}...")
        
        # Step 5: Convert to ClassifiedEvent format for final feed
        converted: List[Dict[str, Any]] = []
        
        for ins in ranked:
            event_id = ins.get("source_event_id") or str(uuid.uuid4())
            
            classified = {
                "event_id": event_id,
                "content_summary": str(ins.get("summary", ""))[:1000],
                "target_agent": ins.get("domain", "unknown"),
                "confidence_score": round(calculate_score(ins), 3),
                "severity": ins.get("severity", "medium"),
                "timestamp": datetime.utcnow().isoformat()
            }
            converted.append(classified)
        
        logger.info(f"[FeedAggregatorAgent] ===== PRODUCED {len(converted)} RANKED EVENTS =====")
        
        return {"final_ranked_feed": converted}
    
    # =========================================================================
    # 3. DATA REFRESHER AGENT
    # =========================================================================
    
    def data_refresher_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates risk dashboard snapshot based on final_ranked_feed.
        
        This implements the "Operational Risk Radar" from your report:
        - logistics_friction: Route risk from mobility data
        - compliance_volatility: Regulatory risk from political data  
        - market_instability: Volatility from economic data
        
        Input: final_ranked_feed
        Output: risk_dashboard_snapshot
        """
        logger.info("[DataRefresherAgent] ===== REFRESHING DASHBOARD =====")
        
        feed = getattr(state, "final_ranked_feed", [])
        
        if not feed:
            logger.info("[DataRefresherAgent] Empty feed - returning zero metrics")
            return {
                "risk_dashboard_snapshot": {
                    "logistics_friction": 0.0,
                    "compliance_volatility": 0.0,
                    "market_instability": 0.0,
                    "avg_confidence": 0.0,
                    "high_priority_count": 0,
                    "total_events": 0,
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
        
        # Compute aggregate metrics
        confidences = [float(item.get("confidence_score", 0.0)) for item in feed]
        avg_confidence = sum(confidences) / len(confidences)
        high_priority_count = sum(1 for c in confidences if c >= 0.7)
        
        # Domain-specific risk mapping
        domain_risks = {}
        for item in feed:
            domain = item.get("target_agent", "unknown")
            score = item.get("confidence_score", 0.0)
            
            if domain not in domain_risks:
                domain_risks[domain] = []
            domain_risks[domain].append(score)
        
        # Calculate domain-specific risk scores
        # Mobility -> Logistics Friction
        mobility_scores = domain_risks.get("mobility", [0.0])
        logistics = sum(mobility_scores) / len(mobility_scores)
        
        # Political -> Compliance Volatility
        political_scores = domain_risks.get("political", [0.0])
        compliance = sum(political_scores) / len(political_scores)
        
        # Market/Economic -> Market Instability
        market_scores = domain_risks.get("market", [0.0]) + domain_risks.get("economical", [0.0])
        if not market_scores:
            market_scores = [0.0]
        market = sum(market_scores) / len(market_scores)
        
        snapshot = {
            "logistics_friction": round(logistics, 3),
            "compliance_volatility": round(compliance, 3),
            "market_instability": round(market, 3),
            "avg_confidence": round(avg_confidence, 3),
            "high_priority_count": high_priority_count,
            "total_events": len(feed),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[DataRefresherAgent] Dashboard Metrics:")
        logger.info(f"  Logistics Friction: {snapshot['logistics_friction']}")
        logger.info(f"  Compliance Volatility: {snapshot['compliance_volatility']}")
        logger.info(f"  Market Instability: {snapshot['market_instability']}")
        logger.info(f"  High Priority Events: {snapshot['high_priority_count']}/{snapshot['total_events']}")
        
        return {"risk_dashboard_snapshot": snapshot}

    # =========================================================================
    # 4. DATA REFRESH ROUTER
    # =========================================================================
    
    def data_refresh_router(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routing decision after dashboard refresh.
        
        CRITICAL: This controls the loop vs. end decision.
        For Continuous Mode, this waits for a set interval and then loops.
        
        Returns:
            {"route": "GraphInitiator"} to loop back
        """
        # [Image of server polling architecture]

        REFRESH_INTERVAL_SECONDS = 60 
        
        logger.info(f"[DataRefreshRouter] Cycle complete. Waiting {REFRESH_INTERVAL_SECONDS}s for next refresh...")
        
        # Blocking sleep to simulate polling interval
        # In a full async production app, you might use asyncio.sleep here
        time.sleep(REFRESH_INTERVAL_SECONDS)
        
        logger.info("[DataRefreshRouter] Waking up. Routing to GraphInitiator.")
        
        # Always return GraphInitiator to create an infinite loop
        return {"route": "GraphInitiator"}