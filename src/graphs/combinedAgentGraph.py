from __future__ import annotations

from datetime import datetime
from typing_extensions import Optional, List, Dict, Any, TypedDict
import operator
import json

import requests
from bs4 import BeautifulSoup
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from src.states.economicalAgentState import EconomicalAgentState
from src.nodes.economicalAgentNode import economicalAgentNode
from src.utils.utils import tool_dmc_alerts, tool_weather_nowcast
from src.llms.groqllm import GroqLLM
from src.graphs.dataRetrievalAgentGraph import DataRetrievalAgentGraph
from src.graphs.meteorologicalAgentGraph import MeteorologicalGraphBuilder
from src.graphs.politicalAgentGraph import PoliticalGraphBuilder
from src.graphs.economicalAgentGraph import EconomicalGraphBuilder
from src.graphs.intelligenceAgentGraph import IntelligenceGraphBuilder
from src.graphs.socialAgentGraph import SocialGraphBuilder
from langgraph.graph import START, END 
from src.nodes.combinedAgentNode import CombinedAgentNode


class CombinedAgentGraphBuilder:
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        social_obj = SocialGraphBuilder(self.llm)
        intelligence_obj = IntelligenceGraphBuilder(self.llm)
        economical_obj = EconomicalGraphBuilder(self.llm)
        political_obj = PoliticalGraphBuilder(self.llm)
        meteorology_obj = MeteorologicalGraphBuilder(self.llm)
        dataRetrival_obj = DataRetrievalAgentGraph(self.llm)

        combined_obj = CombinedAgentNode(self.llm)

        graph_builder = StateGraph(EconomicalAgentState)
        graph_builder.add_node("SocialAgent", social_obj.build_graph())
        graph_builder.add_node("IntelligenceAgent", intelligence_obj.build_graph())
        graph_builder.add_node("EconomicalAgent", economical_obj.build_graph())
        graph_builder.add_node("PoliticalAgent", political_obj.build_graph())
        graph_builder.add_node("MeteorologicalAgent", meteorology_obj.build_graph())
        graph_builder.add_node("DataRetrievalAgent", dataRetrival_obj.build_data_retrieval_agent_graph())

        graph_builder.add_node("FeedAggregatorAgent", combined_obj.feed_aggregator_agent)
        graph_builder.add_node("DataRefresherAgent", combined_obj.data_refresher_agent)
        graph_builder.add_node("DataRefreshRouter", combined_obj.data_refresh_router)
        graph_builder.add_node("GraphInitiator", combined_obj.graph_initiator)  

        graph_builder.add_edge(START, "GraphInitiator")
        graph_builder.add_edge("GraphInitiator", "SocialAgent")
        graph_builder.add_edge("GraphInitiator", "IntelligenceAgent")
        graph_builder.add_edge("GraphInitiator", "EconomicalAgent")
        graph_builder.add_edge("GraphInitiator", "PoliticalAgent")
        graph_builder.add_edge("GraphInitiator", "MeteorologicalAgent")
        graph_builder.add_edge("GraphInitiator", "DataRetrievalAgent")
        graph_builder.add_edge("SocialAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("IntelligenceAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("EconomicalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("PoliticalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("DataRetrievalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("MeteorologicalAgent", "FeedAggregatorAgent")
        graph_builder.add_edge("FeedAggregatorAgent", "DataRefresherAgent")
        graph_builder.add_edge("DataRefresherAgent", "DataRefreshRouter")
        graph_builder.add_edge("DataRefreshRouter", "GraphInitiator")
        graph_builder.add_edge("DataRefreshRouter", END)
        graph = graph_builder.compile()
        return graph

# ============================================================
# RUN (for manual test)
# ============================================================
print("--- RUNNING METEOROLOGICAL AGENT GRAPH ---\n")
llm = GroqLLM().get_llm()
graph = CombinedAgentGraphBuilder(llm).build_graph()
print("Graph created successfully")

