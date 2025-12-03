"""
src/nodes/combinedAgentNode.py
COMPLETE IMPLEMENTATION - Orchestration nodes for ModelX Mother Graph
Implements: GraphInitiator, FeedAggregator, DataRefresher, DataRefreshRouter
UPDATED: Supports 'Opportunity' tracking and new Scoring Logic
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
    2. FeedAggregator - Collects and ranks domain insights (Risks & Opportunities)
    3. DataRefresher - Updates risk dashboard
    4. DataRefreshRouter - Decides to loop or end
    """
    
    def __init__(self, llm):
        self.llm = llm
        # Initialize production storage manager
        self.storage = StorageManager()
        logger.info("[CombinedAgentNode] Initialized with production storage layer")

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
        - Ranks by risk_score + severity + impact_type
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
        
        # Step 3: PRODUCTION DEDUPLICATION - 3-tier pipeline (SQLite → ChromaDB → Accept)
        unique: List[Dict[str, Any]] = []
        dedup_stats = {
            "exact_matches": 0,
            "semantic_matches": 0,
            "unique_events": 0
        }
        
        for ins in flattened:
            summary = str(ins.get("summary", "")).strip()
            if not summary:
                continue
            
            # Use storage manager's 3-tier deduplication
            is_dup, reason, match_data = self.storage.is_duplicate(summary)
            
            if is_dup:
                if reason == "exact_match":
                    dedup_stats["exact_matches"] += 1
                elif reason == "semantic_match":
                    dedup_stats["semantic_matches"] += 1
                    # Link similar events in Neo4j knowledge graph
                    if match_data and "id" in match_data:
                        event_id = ins.get("source_event_id") or str(uuid.uuid4())
                        self.storage.link_similar_events(
                            event_id, 
                            match_data["id"], 
                            match_data.get("similarity", 0.85)
                        )
                continue
            
            # Event is unique - accept it
            dedup_stats["unique_events"] += 1
            unique.append(ins)
        
        logger.info(
            f"[FeedAggregatorAgent] Deduplication complete: "
            f"{dedup_stats['unique_events']} unique, "
            f"{dedup_stats['exact_matches']} exact dups, "
            f"{dedup_stats['semantic_matches']} semantic dups"
        )
        
        # Step 4: Rank by risk_score + severity boost + Opportunity Logic
        severity_boost_map = {
            "low": 0.0,
            "medium": 0.05,
            "high": 0.15,
            "critical": 0.3
        }
        
        def calculate_score(item: Dict[str, Any]) -> float:
            """Calculate composite score for Risks AND Opportunities"""
            base = float(item.get("risk_score", 0.0))
            severity = str(item.get("severity", "low")).lower()
            impact = str(item.get("impact_type", "risk")).lower()
            
            boost = severity_boost_map.get(severity, 0.0)
            
            # Opportunities are also "High Priority" events, so we boost them too
            # to make sure they appear at the top of the feed
            opp_boost = 0.2 if impact == "opportunity" else 0.0
            
            return base + boost + opp_boost
        
        # Sort descending by score
        ranked = sorted(unique, key=calculate_score, reverse=True)
        
        logger.info(f"[FeedAggregatorAgent] Top 3 events by score:")
        for i, ins in enumerate(ranked[:3]):
            score = calculate_score(ins)
            domain = ins.get("domain", "unknown")
            impact = ins.get("impact_type", "risk")
            summary_preview = str(ins.get("summary", ""))[:80]
            logger.info(f"  {i+1}. [{domain}] ({impact}) Score={score:.3f} | {summary_preview}...")
        
        # Step 5: Convert to ClassifiedEvent format AND store in all databases
        converted: List[Dict[str, Any]] = []
        
        for ins in ranked:
            event_id = ins.get("source_event_id") or str(uuid.uuid4())
            summary = str(ins.get("summary", ""))[:1000]
            domain = ins.get("domain", "unknown")
            severity = ins.get("severity", "medium")
            impact_type = ins.get("impact_type", "risk")
            confidence = round(calculate_score(ins), 3)
            timestamp = datetime.utcnow().isoformat()
            
            classified = {
                "event_id": event_id,
                "content_summary": summary,
                "target_agent": domain,
                "confidence_score": confidence,
                "severity": severity,
                "impact_type": impact_type,
                "timestamp": timestamp
            }
            converted.append(classified)
            
            # CRITICAL: Store in all databases (SQLite, ChromaDB, Neo4j)
            self.storage.store_event(
                event_id=event_id,
                summary=summary,
                domain=domain,
                severity=severity,
                impact_type=impact_type,
                confidence_score=confidence,
                timestamp=timestamp
            )
        
        logger.info(f"[FeedAggregatorAgent] ===== PRODUCED {len(converted)} RANKED EVENTS =====") logger.info(f"[FeedAggregatorAgent] ===== STORED IN ALL DATABASES (SQLite+ChromaDB+Neo4j) =====")
        
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
        - opportunity_index: NEW - Growth signals from positive events
        
        Input: final_ranked_feed
        Output: risk_dashboard_snapshot
        """
        logger.info("[DataRefresherAgent] ===== REFRESHING DASHBOARD =====")
        
        feed = getattr(state, "final_ranked_feed", [])
        
        # Default snapshot structure
        snapshot = {
            "logistics_friction": 0.0,
            "compliance_volatility": 0.0,
            "market_instability": 0.0,
            "opportunity_index": 0.0,
            "avg_confidence": 0.0,
            "high_priority_count": 0,
            "total_events": 0,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        if not feed:
            logger.info("[DataRefresherAgent] Empty feed - returning zero metrics")
            return {"risk_dashboard_snapshot": snapshot}
        
        # Compute aggregate metrics
        confidences = [float(item.get("confidence_score", 0.0)) for item in feed]
        avg_confidence = sum(confidences) / len(confidences)
        high_priority_count = sum(1 for c in confidences if c >= 0.7)
        
        # Domain-specific scoring buckets
        domain_risks = {}
        opportunity_scores = []
        
        for item in feed:
            domain = item.get("target_agent", "unknown")
            score = item.get("confidence_score", 0.0)
            impact = item.get("impact_type", "risk")
            
            # Separate Opportunities from Risks
            if impact == "opportunity":
                opportunity_scores.append(score)
            else:
                # Group Risks by Domain
                if domain not in domain_risks:
                    domain_risks[domain] = []
                domain_risks[domain].append(score)
        
        # Helper for calculating averages safely
        def safe_avg(lst):
            return sum(lst) / len(lst) if lst else 0.0
            
        # Calculate domain-specific risk scores
        # Mobility -> Logistics Friction
        mobility_scores = domain_risks.get("mobility", []) + domain_risks.get("social", []) # Social unrest affects logistics
        snapshot["logistics_friction"] = round(safe_avg(mobility_scores), 3)
        
        # Political -> Compliance Volatility
        political_scores = domain_risks.get("political", [])
        snapshot["compliance_volatility"] = round(safe_avg(political_scores), 3)
        
        # Market/Economic -> Market Instability
        market_scores = domain_risks.get("market", []) + domain_risks.get("economical", [])
        snapshot["market_instability"] = round(safe_avg(market_scores), 3)
        
        # NEW: Opportunity Index
        # Higher score means stronger positive signals
        snapshot["opportunity_index"] = round(safe_avg(opportunity_scores), 3)
        
        snapshot["avg_confidence"] = round(avg_confidence, 3)
        snapshot["high_priority_count"] = high_priority_count
        snapshot["total_events"] = len(feed)
        snapshot["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(f"[DataRefresherAgent] Dashboard Metrics:")
        logger.info(f"  Logistics Friction: {snapshot['logistics_friction']}")
        logger.info(f"  Compliance Volatility: {snapshot['compliance_volatility']}")
        logger.info(f"  Market Instability: {snapshot['market_instability']}")
        logger.info(f"  Opportunity Index: {snapshot['opportunity_index']}")
        logger.info(f"  High Priority Events: {snapshot['high_priority_count']}/{snapshot['total_events']}")
        
        # PRODUCTION FEATURE: Export to CSV for archival
        try:
            if feed:
                self.storage.export_feed_to_csv(feed)
                logger.info(f"[DataRefresherAgent] Exported {len(feed)} events to CSV")
        except Exception as e:
            logger.error(f"[DataRefresherAgent] CSV export error: {e}")
        
        # Cleanup old cache entries periodically
        try:
            self.storage.cleanup_old_data()
        except Exception as e:
            logger.error(f"[DataRefresherAgent] Cleanup error: {e}")
        
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