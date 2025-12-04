"""
combinedAgentGraph.py
Main entry point for the Combined Agent System.
FIXED: Added output adapter wrapper to prevent InvalidUpdateError
"""
from __future__ import annotations
import logging
from datetime import datetime

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


# Configure Logging
logger = logging.getLogger("main_graph")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)


# ============================================================================
# OUTPUT ADAPTER WRAPPER (CRITICAL FIX FOR INVALIDUPDATEERROR)
# ============================================================================
def wrap_subagent_with_adapter(subagent_graph, agent_name: str):
    """
    CRITICAL WRAPPER: Converts sub-agent output to CombinedAgentState format.
    
    Problem: Sub-agents use their own state classes (SocialAgentState, etc.)
    Solution: This wrapper extracts relevant data and formats it as domain_insights
    
    Returns:
        A wrapped function that returns {"domain_insights": [data]}
    """
    def wrapped_agent(state):
        try:
            # Execute the sub-agent with its own state
            result = subagent_graph.invoke(state)
            
            # Extract meaningful data from sub-agent result
            # Each sub-agent returns different state structures, 
            # so we wrap the entire result
            insight = {
                "source": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_output": result,  # Complete sub-agent state
                "status": "completed"
            }
            
            # CRITICAL: Must return as a LIST within domain_insights
            logger.info(f"[{agent_name}] Formatted output for CombinedAgent")
            return {"domain_insights": [insight]}
            
        except Exception as e:
            # Error handling: Return error as insight to prevent crash
            logger.error(f"[{agent_name}] Error: {e}")
            return {"domain_insights": [{
                "source": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            }]}
    
    return wrapped_agent


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

        # 2. Initialize Main Orchestrator Node
        orchestrator = CombinedAgentNode(self.llm)

        # 3. Create State Graph
        workflow = StateGraph(CombinedAgentState)

        # 4. Add Sub-Graph Nodes with Adapter Wrappers (CRITICAL FIX)
        workflow.add_node("SocialAgent", 
                         wrap_subagent_with_adapter(social.build_graph(), "SocialAgent"))
        workflow.add_node("IntelligenceAgent", 
                         wrap_subagent_with_adapter(intelligence.build_graph(), "IntelligenceAgent"))
        workflow.add_node("EconomicalAgent", 
                         wrap_subagent_with_adapter(economical.build_graph(), "EconomicalAgent"))
        workflow.add_node("PoliticalAgent", 
                         wrap_subagent_with_adapter(political.build_graph(), "Political Agent"))
        workflow.add_node("MeteorologicalAgent", 
                         wrap_subagent_with_adapter(meteorological.build_graph(), "MeteorologicalAgent"))

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
            "PoliticalAgent", "MeteorologicalAgent"
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
print("--- BUILDING COMBINED AGENT GRAPH (WITH ADAPTER FIX) ---")
llm = GroqLLM().get_llm()
builder = CombinedAgentGraphBuilder(llm)
graph = builder.build_graph()
print("✓ Combined ModelX Graph built successfully with InvalidUpdateError fix")