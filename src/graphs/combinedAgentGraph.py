"""
combinedAgentGraph.py
Main entry point for the Combined Agent System.
"""
from __future__ import annotations
import logging

# LangGraph Imports
from langgraph.graph import StateGraph, START, END

# Project Imports
from src.llms.groqllm import GroqLLM
from src.states.combinedAgentState import CombinedAgentState
from src.nodes.combinedAgentNode import CombinedAgentNode

# Import Sub-Graph Builders
from src.graphs.socialAgentGraph import SocialGraphBuilder
from src.graphs.intelligenceAgentGraph import IntelligenceGraphBuilder
from src.graphs.economicalAgentGraph import EconomicalGraphBuilder
from src.graphs.politicalAgentGraph import PoliticalGraphBuilder
from src.graphs.meteorologicalAgentGraph import MeteorologicalGraphBuilder
from src.graphs.dataRetrievalAgentGraph import DataRetrievalAgentGraph

# Configure Logging
logger = logging.getLogger("main_graph")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

class CombinedAgentGraphBuilder:
    def __init__(self, llm):
        self.llm = llm

    def build_graph(self):
        # 1. Initialize Sub-Graph Builders
        social = SocialGraphBuilder(self.llm)
        intelligence = IntelligenceGraphBuilder(self.llm)
        economical = EconomicalGraphBuilder(self.llm)
        political = PoliticalGraphBuilder(self.llm)
        meteorological = MeteorologicalGraphBuilder(self.llm)
        data_retrieval = DataRetrievalAgentGraph(self.llm)

        # 2. Initialize Main Orchestrator Node
        orchestrator = CombinedAgentNode(self.llm)

        # 3. Create State Graph
        workflow = StateGraph(CombinedAgentState)

        # 4. Add Sub-Graph Nodes (Fan-Out)
        workflow.add_node("SocialAgent", social.build_graph())
        workflow.add_node("IntelligenceAgent", intelligence.build_graph())
        workflow.add_node("EconomicalAgent", economical.build_graph())
        workflow.add_node("PoliticalAgent", political.build_graph())
        workflow.add_node("MeteorologicalAgent", meteorological.build_graph())
        workflow.add_node("DataRetrievalAgent", data_retrieval.build_data_retrieval_agent_graph())

        # 5. Add Orchestration Nodes (Fan-In)
        workflow.add_node("GraphInitiator", orchestrator.graph_initiator)
        workflow.add_node("FeedAggregatorAgent", orchestrator.feed_aggregator_agent)
        workflow.add_node("DataRefresherAgent", orchestrator.data_refresher_agent)
        workflow.add_node("DataRefreshRouter", orchestrator.data_refresh_router)

        # 6. Define Edges
        # Start -> Initiator
        workflow.add_edge(START, "GraphInitiator")

        # Initiator -> All Sub-Agents (Parallel)
        sub_agents = [
            "SocialAgent", "IntelligenceAgent", "EconomicalAgent",
            "PoliticalAgent", "MeteorologicalAgent", "DataRetrievalAgent"
        ]
        for agent in sub_agents:
            workflow.add_edge("GraphInitiator", agent)
            workflow.add_edge(agent, "FeedAggregatorAgent")

        # Aggregator -> Refresher -> Router
        workflow.add_edge("FeedAggregatorAgent", "DataRefresherAgent")
        workflow.add_edge("DataRefresherAgent", "DataRefreshRouter")

        # 7. Conditional Routing
        workflow.add_conditional_edges(
            "DataRefreshRouter",
            lambda x: x.route if x.route else "END",
            {
                "GraphInitiator": "GraphInitiator",
                "END": END
            }
        )

        return workflow.compile()

# --- GLOBAL EXPORT FOR LANGGRAPH DEV ---
# This code runs when the file is imported.
# It instantiates the LLM and builds the graph object.
print("--- BUILDING COMBINED AGENT GRAPH ---")
llm = GroqLLM().get_llm()
builder = CombinedAgentGraphBuilder(llm)
graph = builder.build_graph()
print("Combined ModelX Graph built successfully.")