from __future__ import annotations

from datetime import datetime
from typing_extensions import Optional, List, Dict, Any, TypedDict
import operator
import json

import requests
from bs4 import BeautifulSoup
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from src.states.politicalAgentState import PoliticalAgentState
from src.nodes.politicalAgentNode import PoliticalAgentNode
from src.utils.utils import tool_dmc_alerts, tool_weather_nowcast
from src.llms.groqllm import GroqLLM

class PoliticalGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        meteorology_obj = PoliticalAgentNode(self.llm)
        worker_graph_builder = StateGraph(PoliticalAgentState)
        worker_graph_builder.add_node("meteorological_worker", meteorology_obj.meteorological_worker_agent)
        worker_graph_builder.add_node("tool_node", meteorology_obj.tool_node)

        worker_graph_builder.set_entry_point("meteorological_worker")
        worker_graph_builder.add_edge("meteorological_worker", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)

        worker_graph = worker_graph_builder.compile()

        # ============================================================
        # BUILD MAIN METEOROLOGICAL AGENT GRAPH
        # ============================================================

        main_graph_builder = StateGraph(PoliticalAgentState)

        # Nodes
        main_graph_builder.add_node("data_change_detector", meteorology_obj.data_change_detector)
        main_graph_builder.add_node("task_delegator", meteorology_obj.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", meteorology_obj.prepare_worker_tasks)

        # Orchestrator-worker workflow (inside dotted box)
        main_graph_builder.add_node(
            "meteorological_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))},
        )
        main_graph_builder.add_node("aggregate_results", meteorology_obj.aggregate_results)

        # Feed creator
        main_graph_builder.add_node("feed_creator", meteorology_obj.feed_creator_agent)

        # Edges (linear, exactly like the diagram)
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "meteorological_workers")
        main_graph_builder.add_edge("meteorological_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        main_graph_builder.add_edge("feed_creator", END)

        graph = main_graph_builder.compile()
        return graph

# ============================================================
# RUN (for manual test)
# ============================================================
print("--- RUNNING METEOROLOGICAL AGENT GRAPH ---\n")
llm = GroqLLM().get_llm()
graph = PoliticalGraphBuilder(llm).build_graph()
print("Graph created successfully")

