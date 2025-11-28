"""
combined_agent_graph.py

Corrected CombinedAgentGraphBuilder and implemented CombinedAgentNode nodes
(feed aggregator, data refresher, data refresh router, graph initiator).

Notes / design choices:
- The original used `StateGraph(EconomicalAgentState)` which ties the whole graph
  to a single agent state type (incorrect for a combined graph). Here we declare
  a small CombinedAgentState that composes minimal fields used by the combined
  node. This keeps the graph builder self-contained while remaining easy to
  adapt to your project-wide state types.
- CombinedAgentNode methods are implemented as defensive callables that accept
  either a passed `state` object or keyword arguments (this makes them easier to
  integrate into the rest of your codebase and langgraph wiring). They:
    - attempt to read domain outputs from the execution state,
    - perform simple aggregation, ranking and state updates,
    - return control information (router returns a dict with `route`).
- There are placeholders where you should plug your project's richer logic /
  LLM invocations (the implementation is intentionally conservative).
- This file only corrects and implements the graph + node code you asked for.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
import operator
import json
import uuid
import logging

# External libs / project imports (kept as in your original snippet)
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, get_buffer_string

# These imports mirror your provided snippet; make sure the referenced modules exist
from src.states.dataRetrievalAgentState import (
    DataRetrievalAgentState,
    ScrapingTask,
    RawScrapedData,
    ClassifiedEvent as DR_ClassifiedEvent,
)
from src.states.economicalAgentState import EconomicalAgentState
from src.nodes.economicalAgentNode import economicalAgentNode
from src.utils.prompts import MASTER_AGENT_SYSTEM_PROMPT, MASTER_AGENT_HUMAN_PROMPT
from src.utils.utils import get_today_str, TOOL_MAPPING

# Graph builders for the domain agents (assumed to exist in your project)
from src.graphs.dataRetrievalAgentGraph import DataRetrievalAgentGraph
from src.graphs.meteorologicalAgentGraph import MeteorologicalGraphBuilder
from src.graphs.politicalAgentGraph import PoliticalGraphBuilder
from src.graphs.economicalAgentGraph import EconomicalGraphBuilder
from src.graphs.intelligenceAgentGraph import IntelligenceGraphBuilder
from src.graphs.socialAgentGraph import SocialGraphBuilder

# Your LLM wrapper (kept as in snippet)
from src.llms.groqllm import GroqLLM

# logging
logger = logging.getLogger("combined_agent_graph")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)


# -------------------------------------------
# Minimal combined state (keeps graph generic)
# -------------------------------------------
from pydantic import BaseModel, Field


class CombinedAgentState(BaseModel):
    """
    Minimal state used by the combined graph.
    You can replace / extend this with your project's canonical State classes.
    """
    # Raw scraped items (from DataRetrievalAgent)
    raw_scraped: List[Dict[str, Any]] = Field(default_factory=list)

    # Per-domain outputs (each builder/node may store DomainInsight-like dicts here)
    domain_insights: List[Dict[str, Any]] = Field(default_factory=list)

    # Final aggregated / ranked feed (list of ClassifiedEvent-like dicts)
    final_ranked_feed: List[Dict[str, Any]] = Field(default_factory=list)

    # Dashboard / Risk snapshot (simple dict - replace with RiskMetrics model if preferred)
    risk_snapshot: Dict[str, float] = Field(default_factory=dict)

    # Misc
    last_run_ts: Optional[datetime] = None
    run_count: int = 0
    max_runs: int = 5  # safety cap for demo/integration


# -------------------------------------------
# CombinedAgentNode implementation
# -------------------------------------------
class CombinedAgentNode:
    """
    Implements the top-level combined node functions used by the StateGraph:
      - graph_initiator
      - feed_aggregator_agent
      - data_refresher_agent
      - data_refresh_router

    Each method is intentionally tolerant in signature (accepts `state` or **kwargs).
    The langgraph runtime in your project may call these with different parameters;
    adapt as needed.
    """

    def __init__(self, llm):
        self.llm = llm

    # --- Graph Initiator ------------------------------------------------
    def graph_initiator(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Initialization step executed at START in the graph.
        Responsibilities:
          - update run_count / last_run_ts in state
          - optionally trigger pre-load / housekeeping
          - return a simple status dict
        """
        logger.info("[GraphInitiator] starting graph iteration")
        if state is None:
            state = kwargs.get("state")
        if state is not None:
            state.run_count = (state.run_count or 0) + 1
            state.last_run_ts = datetime.utcnow()
            logger.info(f"[GraphInitiator] run_count={state.run_count}")

        # Potential place to insert system prompts or LLM warm-up calls
        return {"status": "initiated", "run_count": getattr(state, "run_count", None)}

    # --- Feed Aggregator ------------------------------------------------
    def feed_aggregator_agent(self, state: Optional[CombinedAgentState] = None, **kwargs) -> List[DR_ClassifiedEvent]:
        """
        Aggregates outputs from domain agents (expected to be stored in `state.domain_insights`).
        - flatten domain insights
        - deduplicate (naive by summary text)
        - simple ranking by risk_score + severity
        - convert to ClassifiedEvent-like dicts and save into state.final_ranked_feed

        Returns list of ClassifiedEvent-like dicts (DR_ClassifiedEvent.dict-compatible).
        """
        logger.info("[FeedAggregatorAgent] running aggregation")
        if state is None:
            state = kwargs.get("state")
        # Attempt to gather incoming domain insights from kwargs if not in state
        incoming: List[Dict[str, Any]] = []
        if state is not None and isinstance(state.domain_insights, list):
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

        # Convert top-N into ClassifiedEvent-like objects (project's DR_ClassifiedEvent)
        converted: List[DR_ClassifiedEvent] = []
        for ins in ranked:
            # generate unique event id if missing
            event_id = ins.get("source_event_id") or str(uuid.uuid4())
            classified = DR_ClassifiedEvent(
                event_id=event_id,
                content_summary=ins.get("summary", "")[:1000],
                target_agent=ins.get("domain", "unknown"),
                confidence_score=round(float(ins.get("risk_score", 0.0)), 3),
            )
            converted.append(classified)

        # Persist to state
        if state is not None:
            state.final_ranked_feed = [c.dict() for c in converted]

        logger.info(f"[FeedAggregatorAgent] produced {len(converted)} classified events (ranked)")
        return converted

    # --- Data Refresher -------------------------------------------------
    def data_refresher_agent(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Update dashboards, produce snapshots and perform any refresh operations on the aggregated feed.
        - read state.final_ranked_feed
        - compute simple risk snapshot metrics and attach to state.risk_snapshot
        - returns a dict with summary statistics
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
            # clear snapshot
            if state is not None:
                state.risk_snapshot = {}
            return {"updated": False, "reason": "empty_feed"}

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

        if state is not None:
            state.risk_snapshot = snapshot

        logger.info(f"[DataRefresherAgent] snapshot updated: avg_conf={snapshot['avg_confidence']} high_count={snapshot['high_priority_count']}")
        return {"updated": True, "snapshot": snapshot}

    # --- Data Refresh Router -------------------------------------------
    def data_refresh_router(self, state: Optional[CombinedAgentState] = None, **kwargs) -> Dict[str, Any]:
        """
        Routing decision after data refresher: determines whether to loop back to GraphInitiator or end.
        Policy (example, replace with your app policy):
          - If there is any classified event with confidence >= 0.85 and run_count < max_runs => loop
          - Otherwise => end
        Returns: {"route": "GraphInitiator"} or {"route": "END"} (langgraph edges expected)
        """
        logger.info("[DataRefreshRouter] making routing decision")
        if state is None:
            state = kwargs.get("state")

        feed = []
        if state is not None:
            feed = state.final_ranked_feed or []
        else:
            feed = kwargs.get("final_ranked_feed", [])

        if not feed:
            logger.info("[DataRefreshRouter] empty final feed -> ending")
            return {"route": END}

        top_conf = max(float(item.get("confidence_score", 0.0)) for item in feed)
        logger.info(f"[DataRefreshRouter] top_confidence={top_conf}")

        # Decision thresholds
        if top_conf >= 0.85 and (state is None or state.run_count < state.max_runs):
            logger.info("[DataRefreshRouter] threshold met, looping back to GraphInitiator")
            return {"route": "GraphInitiator"}
        else:
            logger.info("[DataRefreshRouter] no loop condition met, routing to END")
            return {"route": END}


# -------------------------------------------
# Corrected CombinedAgentGraphBuilder
# -------------------------------------------
class CombinedAgentGraphBuilder:
    """
    Builds the combined state graph connecting domain agent graphs plus the combined orchestration nodes.
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

        # Use a combined state model rather than EconomicalAgentState for the overall graph.
        graph_builder = StateGraph(CombinedAgentState)

        # Add domain subgraphs; these builders are expected to return a callable/node or subgraph object
        graph_builder.add_node("SocialAgent", social_obj.build_graph())
        graph_builder.add_node("IntelligenceAgent", intelligence_obj.build_graph())
        graph_builder.add_node("EconomicalAgent", economical_obj.build_graph())
        graph_builder.add_node("PoliticalAgent", political_obj.build_graph())
        graph_builder.add_node("MeteorologicalAgent", meteorology_obj.build_graph())
        graph_builder.add_node("DataRetrievalAgent", dataRetrieval_obj.build_data_retrieval_agent_graph())

        # Add the combined orchestration nodes implemented above
        graph_builder.add_node("FeedAggregatorAgent", combined_obj.feed_aggregator_agent)
        graph_builder.add_node("DataRefresherAgent", combined_obj.data_refresher_agent)
        graph_builder.add_node("DataRefreshRouter", combined_obj.data_refresh_router)
        graph_builder.add_node("GraphInitiator", combined_obj.graph_initiator)

        # Wiring according to the architecture diagram you provided
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

        # Router can loop back to GraphInitiator or end
        graph_builder.add_edge("DataRefreshRouter", "GraphInitiator")
        graph_builder.add_edge("DataRefreshRouter", END)

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
