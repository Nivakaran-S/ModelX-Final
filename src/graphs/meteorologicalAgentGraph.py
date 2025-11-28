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
from src.states.meteorologicalAgentState import MeteorologicalAgentState
from src.nodes.meteorologicalAgentNode import MeteorologicalAgentNode
from src.llms.groqllm import GroqLLM

class MeteorologicalGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        # Variable name is logically correct here, but let's ensure consistency
        meteorology_node = MeteorologicalAgentNode(self.llm)
        
        # --- Worker Sub-Graph ---
        worker_graph_builder = StateGraph(MeteorologicalAgentState)
        worker_graph_builder.add_node("worker_agent", meteorology_node.meteorological_worker_agent)
        worker_graph_builder.add_node("tool_node", meteorology_node.tool_node)

        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)

        worker_graph = worker_graph_builder.compile()

        # ============================================================
        # BUILD MAIN METEOROLOGICAL AGENT GRAPH
        # ============================================================

        main_graph_builder = StateGraph(MeteorologicalAgentState)

        # Nodes
        main_graph_builder.add_node("data_change_detector", meteorology_node.data_change_detector)
        main_graph_builder.add_node("task_delegator", meteorology_node.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", meteorology_node.prepare_worker_tasks)

        # Orchestrator-worker workflow
        main_graph_builder.add_node(
            "meteorological_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))},
        )
        main_graph_builder.add_node("aggregate_results", meteorology_node.aggregate_results)

        # Feed creator
        main_graph_builder.add_node("feed_creator", meteorology_node.feed_creator_agent)

        # --- ADAPTER NODE ---
        def format_output(state):
            """Wraps the string feed into the object format expected by the parent graph."""
            feed_text = state.get("final_feed", "No updates.")
            insight = {
                "source_event_id": str(uuid.uuid4()),
                "domain": "weather",
                "severity": "medium", 
                "summary": feed_text,
                "risk_score": 0.4
            }
            return {"domain_insights": [insight]}

        main_graph_builder.add_node("format_output", format_output)

        # Edges
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "meteorological_workers")
        main_graph_builder.add_edge("meteorological_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        
        # Route to formatter
        main_graph_builder.add_edge("feed_creator", "format_output")
        main_graph_builder.add_edge("format_output", END)

        graph = main_graph_builder.compile()
        return graph

# ============================================================
# RUN (for manual test)
# ============================================================

print("--- RUNNING METEOROLOGICAL AGENT GRAPH ---\n")
llm = GroqLLM().get_llm()
graph = MeteorologicalGraphBuilder(llm).build_graph()
print("Graph created successfully")