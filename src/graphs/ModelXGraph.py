"""
combined_agent_graph.py

Corrected CombinedAgentGraphBuilder and implemented CombinedAgentNode nodes
(feed aggregator, data refresher, data refresh router, graph initiator).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
import operator
import json
import uuid
import logging

# External libs / project imports
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, get_buffer_string

# These imports mirror your provided snippet
from src.states.dataRetrievalAgentState import (
    DataRetrievalAgentState,
    ScrapingTask,
    RawScrapedData,
    ClassifiedEvent as DR_ClassifiedEvent,
)
# Note: We use a custom CombinedAgentState here, but we import builders
from src.graphs.dataRetrievalAgentGraph import DataRetrievalAgentGraph
from src.graphs.meteorologicalAgentGraph import MeteorologicalGraphBuilder
from src.graphs.politicalAgentGraph import PoliticalGraphBuilder
from src.graphs.economicalAgentGraph import EconomicalGraphBuilder
from src.graphs.intelligenceAgentGraph import IntelligenceGraphBuilder
from src.graphs.socialAgentGraph import SocialGraphBuilder

from src.llms.groqllm import GroqLLM

# logging
logger = logging.getLogger("combined_agent_graph")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)


# -------------------------------------------
# Minimal combined state
# -------------------------------------------
from pydantic import BaseModel, Field


class CombinedAgentState(BaseModel):
    """
    Minimal state used by the combined graph.
    """
    # Raw scraped items (from DataRetrievalAgent)
    raw_scraped: List[Dict[str, Any]] = Field(default_factory=list)

    # Per-domain outputs (each builder/node may store DomainInsight-like dicts here)
    domain_insights: List[Dict[str, Any]] = Field(default_factory=list)

    # Final aggregated / ranked feed (list of ClassifiedEvent-like dicts)
    final_ranked_feed: List[Dict[str, Any]] = Field(default_factory=list)

    # Dashboard / Risk snapshot
    risk_snapshot: Dict[str, float] = Field(default_factory=dict)

    # Misc
    last_run_ts: Optional[datetime] = None
    run_count: int = 0
    max_runs: int = 5  # safety cap for demo/integration
    
    # Control flow (Added to track router decision)
    route: Optional[str] = None


# -------------------------------------------
# CombinedAgentNode implementation
# -------------------------------------------
class CombinedAgentNode:
    """
    Implements the top-level combined node functions used by the StateGraph.
    """

    def __init__(self, llm):
        self.llm = llm

    # --- Graph Initiator ------------------------------------------------
    def graph_initiator(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Initialization step executed at START in the graph.
        """
        logger.info("[GraphInitiator] starting graph iteration")
        if state is None:
            state = kwargs.get("state")
            
        run_count = 0
        if state is not None:
            run_count = (state.run_count or 0) + 1
            logger.info(f"[GraphInitiator] run_count={run_count}")

        return {
            "status": "initiated", 
            "run_count": run_count, 
            "last_run_ts": datetime.utcnow()
        }

    # --- Feed Aggregator ------------------------------------------------
    def feed_aggregator_agent(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Aggregates outputs from domain agents.
        """
        logger.info("[FeedAggregatorAgent] running aggregation")
        if state is None:
            state = kwargs.get("state")
            
        # Attempt to gather incoming domain insights
        incoming: List[Dict[str, Any]] = []
        if state is not None and state.domain_insights:
            incoming = list(state.domain_insights)
        else:
            incoming = kwargs.get("domain_insights", [])

        # Flatten if nested lists
        flattened: List[Dict[str, Any]] = []
        for item in incoming:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)

        logger.info(f"[FeedAggregatorAgent] received {len(flattened)} raw insights")

        # Naive dedupe by summary prefix
        seen = set()
        unique: List[Dict[str, Any]] = []
        for ins in flattened:
            summary = str(ins.get("summary", "")).strip()
            key = summary[:120]
            if key not in seen:
                seen.add(key)
                unique.append(ins)

        # Ranking: use risk_score (0..1) and severity boost
        severity_boost_map = {"low": 0.0, "medium": 0.05, "high": 0.15, "critical": 0.3}
        def score(item):
            base = float(item.get("risk_score", 0.0))
            sev = str(item.get("severity", "low"))
            return base + severity_boost_map.get(sev, 0.0)

        ranked = sorted(unique, key=score, reverse=True)

        # Convert top-N into ClassifiedEvent-like objects
        converted: List[Dict[str, Any]] = []
        for ins in ranked:
            event_id = ins.get("source_event_id") or str(uuid.uuid4())
            classified = {
                "event_id": event_id,
                "content_summary": ins.get("summary", "")[:1000],
                "target_agent": ins.get("domain", "unknown"),
                "confidence_score": round(float(ins.get("risk_score", 0.0)), 3),
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
        if state is None:
            state = kwargs.get("state")

        feed = []
        if state is not None:
            feed = state.final_ranked_feed or []
        else:
            feed = kwargs.get("final_ranked_feed", [])

        if not feed:
            logger.info("[DataRefresherAgent] no feed to refresh")
            return {"updated": False, "reason": "empty_feed", "risk_snapshot": {}}

        # compute simple metrics
        confidences = [float(item.get("confidence_score", 0.0)) for item in feed]
        avg_conf = sum(confidences) / max(1, len(confidences))
        high_count = sum(1 for c in confidences if c >= 0.7)

        # Heuristic mapping -> risk_snapshot
        snapshot = {
            "avg_confidence": round(avg_conf, 3),
            "high_priority_count": int(high_count),
            "last_updated": datetime.utcnow().isoformat(),
        }

        logger.info(f"[DataRefresherAgent] snapshot updated: avg_conf={snapshot['avg_confidence']} high_count={snapshot['high_priority_count']}")
        return {"updated": True, "risk_snapshot": snapshot}

    # --- Data Refresh Router -------------------------------------------
    def data_refresh_router(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Routing decision after data refresher.
        """
        logger.info("[DataRefreshRouter] making routing decision")
        if state is None:
            state = kwargs.get("state")

        feed = []
        run_count = 0
        max_runs = 5
        
        if state is not None:
            feed = state.final_ranked_feed or []
            run_count = state.run_count
            max_runs = state.max_runs
        else:
            feed = kwargs.get("final_ranked_feed", [])

        if not feed:
            logger.info("[DataRefreshRouter] empty final feed -> ending")
            return {"route": "END"}

        top_conf = max(float(item.get("confidence_score", 0.0)) for item in feed)
        logger.info(f"[DataRefreshRouter] top_confidence={top_conf}")

        # Decision thresholds
        if top_conf >= 0.85 and run_count < max_runs:
            logger.info("[DataRefreshRouter] threshold met, looping back to GraphInitiator")
            return {"route": "GraphInitiator"}
        else:
            logger.info("[DataRefreshRouter] no loop condition met, routing to END")
            return {"route": "END"}


# -------------------------------------------
# Corrected CombinedAgentGraphBuilder
# -------------------------------------------
class CombinedAgentGraphBuilder:
    """
    Builds the combined state graph.
    """

    def __init__(self, llm):
        self.llm = llm

    def build_graph(self):
        # instantiate domain graph builders
        social_obj = SocialGraphBuilder(self.llm)
        intelligence_obj = IntelligenceGraphBuilder(self.llm)
        economical_obj = EconomicalGraphBuilder(self.llm)
        political_obj = PoliticalGraphBuilder(self.llm)
        meteorology_obj = MeteorologicalGraphBuilder(self.llm)
        dataRetrieval_obj = DataRetrievalAgentGraph(self.llm)

        combined_obj = CombinedAgentNode(self.llm)

        # Use a combined state model
        graph_builder = StateGraph(CombinedAgentState)

        # Add domain subgraphs
        graph_builder.add_node("SocialAgent", social_obj.build_graph())
        graph_builder.add_node("IntelligenceAgent", intelligence_obj.build_graph())
        graph_builder.add_node("EconomicalAgent", economical_obj.build_graph())
        graph_builder.add_node("PoliticalAgent", political_obj.build_graph())
        graph_builder.add_node("MeteorologicalAgent", meteorology_obj.build_graph())
        graph_builder.add_node("DataRetrievalAgent", dataRetrieval_obj.build_data_retrieval_agent_graph())

        # Add the combined orchestration nodes
        graph_builder.add_node("FeedAggregatorAgent", combined_obj.feed_aggregator_agent)
        graph_builder.add_node("DataRefresherAgent", combined_obj.data_refresher_agent)
        graph_builder.add_node("DataRefreshRouter", combined_obj.data_refresh_router)
        graph_builder.add_node("GraphInitiator", combined_obj.graph_initiator)

        # Wiring
        graph_builder.add_edge(START, "GraphInitiator")

        # GraphInitiator fans out to domain agents (parallel)
        graph_builder.add_edge("GraphInitiator", "SocialAgent")
        graph_builder.add_edge("GraphInitiator", "IntelligenceAgent")
        graph_builder.add_edge("GraphInitiator", "EconomicalAgent")
        graph_builder.add_edge("GraphInitiator", "PoliticalAgent")
        graph_builder.add_edge("GraphInitiator", "MeteorologicalAgent")
        graph_builder.add_edge("GraphInitiator", "DataRetrievalAgent")

        # Domain agents feed aggregator
        graph_builder.add_edge("SocialAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("IntelligenceAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("EconomicalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("PoliticalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("DataRetrievalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("MeteorologicalAgent", "FeedAggregatorAgent")

        # Aggregation -> refresher -> router
        graph_builder.add_edge("FeedAggregatorAgent", "DataRefresherAgent")
        graph_builder.add_edge("DataRefresherAgent", "DataRefreshRouter")

        # Router with Conditional Logic
        graph_builder.add_conditional_edges(
            "DataRefreshRouter",
            lambda x: x.route if x.route and x.route != "END" else END,
            {
                "GraphInitiator": "GraphInitiator",
                END: END
            }
        )

        # Compile and return the graph
        graph = graph_builder.compile()
        logger.info("[CombinedAgentGraphBuilder] graph compiled successfully")
        return graph


# -------------------------------------------
# Quick manual test (non-invasive)
# -------------------------------------------
print("--- BUILDING COMBINED AGENT GRAPH (test) ---")
llm = GroqLLM().get_llm()
builder = CombinedAgentGraphBuilder(llm)
graph = builder.build_graph()
print("Graph created successfully")