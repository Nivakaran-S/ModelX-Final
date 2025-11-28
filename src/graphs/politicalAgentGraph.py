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
from src.states.politicalAgentState import PoliticalAgentState
from src.nodes.politicalAgentNode import PoliticalAgentNode
from src.llms.groqllm import GroqLLM

class PoliticalGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        # Fixed: Naming convention (was meteorology_obj)
        political_node = PoliticalAgentNode(self.llm)
        
        # --- Worker Sub-Graph ---
        worker_graph_builder = StateGraph(PoliticalAgentState)
        # Note: Verify 'political_worker_agent' exists in your node class
        worker_graph_builder.add_node("worker_agent", political_node.political_worker_agent)
        worker_graph_builder.add_node("tool_node", political_node.tool_node)

        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)

        worker_graph = worker_graph_builder.compile()

        # ============================================================
        # BUILD MAIN POLITICAL AGENT GRAPH
        # ============================================================

        main_graph_builder = StateGraph(PoliticalAgentState)

        # Nodes
        main_graph_builder.add_node("data_change_detector", political_node.data_change_detector)
        main_graph_builder.add_node("task_delegator", political_node.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", political_node.prepare_worker_tasks)

        # Orchestrator-worker workflow
        main_graph_builder.add_node(
            "political_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))},
        )
        main_graph_builder.add_node("aggregate_results", political_node.aggregate_results)

        # Feed creator
        main_graph_builder.add_node("feed_creator", political_node.feed_creator_agent)

        # --- ADAPTER NODE ---
        def format_output(state):
            """Wraps the string feed into the object format expected by the parent graph."""
            feed_text = state.get("final_feed", "No updates.")
            insight = {
                "source_event_id": str(uuid.uuid4()),
                "domain": "political",
                "severity": "high", # Example default, agent logic should determine this
                "summary": feed_text,
                "risk_score": 0.7
            }
            return {"domain_insights": [insight]}

        main_graph_builder.add_node("format_output", format_output)

        # Edges
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "political_workers")
        main_graph_builder.add_edge("political_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        
        # Route to formatter
        main_graph_builder.add_edge("feed_creator", "format_output")
        main_graph_builder.add_edge("format_output", END)

        graph = main_graph_builder.compile()
        return graph

# ============================================================
# RUN (for manual test)
# ============================================================

print("--- RUNNING POLITICAL AGENT GRAPH ---\n")
llm = GroqLLM().get_llm()
graph = PoliticalGraphBuilder(llm).build_graph()
print("POLITICAL AGENT Graph created successfully")