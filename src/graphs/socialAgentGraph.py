from __future__ import annotations

from datetime import datetime
from typing_extensions import Optional, List, Dict, Any, TypedDict
import operator
import json
import uuid

import requests
from bs4 import BeautifulSoup
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from src.states.socialAgentState import SocialAgentState
from src.nodes.socialAgentNode import SocialAgentNode
from src.utils.utils import tool_dmc_alerts, tool_weather_nowcast
from src.llms.groqllm import GroqLLM

class SocialGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        # Corrected: Instantiate SocialAgentNode, not meteorology
        social_node = SocialAgentNode(self.llm)
        
        # --- Worker Sub-Graph ---
        worker_graph_builder = StateGraph(SocialAgentState)
        # Note: Ensure 'social_worker_agent' exists in your SocialAgentNode class. 
        # If it is named 'meteorological_worker_agent', rename it here.
        worker_graph_builder.add_node("worker_agent", social_node.social_worker_agent)
        worker_graph_builder.add_node("tool_node", social_node.tool_node)

        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)

        worker_graph = worker_graph_builder.compile()

        # ============================================================
        # BUILD MAIN SOCIAL AGENT GRAPH
        # ============================================================

        main_graph_builder = StateGraph(SocialAgentState)

        # Nodes
        main_graph_builder.add_node("data_change_detector", social_node.data_change_detector)
        main_graph_builder.add_node("task_delegator", social_node.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", social_node.prepare_worker_tasks)

        # Orchestrator-worker workflow (inside dotted box)
        main_graph_builder.add_node(
            "social_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))},
        )
        main_graph_builder.add_node("aggregate_results", social_node.aggregate_results)

        # Feed creator
        main_graph_builder.add_node("feed_creator", social_node.feed_creator_agent)

        # --- ADAPTER NODE (Crucial for Parent Graph Integration) ---
        def format_output(state):
            """Wraps the string feed into the object format expected by the parent graph."""
            feed_text = state.get("final_feed", "No updates.")
            insight = {
                "source_event_id": str(uuid.uuid4()),
                "domain": "social",
                "severity": "medium", 
                "summary": feed_text,
                "risk_score": 0.5
            }
            # Return list of dicts to match domain_insights signature
            return {"domain_insights": [insight]}

        main_graph_builder.add_node("format_output", format_output)

        # Edges (linear, exactly like the diagram)
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "social_workers")
        main_graph_builder.add_edge("social_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        
        # Route to formatter before ending
        main_graph_builder.add_edge("feed_creator", "format_output")
        main_graph_builder.add_edge("format_output", END)

        graph = main_graph_builder.compile()
        return graph

# ============================================================
# RUN (for manual test)
# ============================================================

print("--- RUNNING SOCIAL AGENT GRAPH ---\n")
llm = GroqLLM().get_llm()
graph = SocialGraphBuilder(llm).build_graph()
print("SOCIAL AGENT Graph created successfully")