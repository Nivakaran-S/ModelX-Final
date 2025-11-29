"""
src/graphs/intelligenceAgentGraph.py
COMPLETE - Intelligence Agent Graph Builder
"""
import uuid
from langgraph.graph import StateGraph, END
from src.states.intelligenceAgentState import IntelligenceAgentState
from src.nodes.intelligenceAgentNode import intelligenceAgentNode
from src.llms.groqllm import GroqLLM


class IntelligenceGraphBuilder:
    """
    Builds the Intelligence Agent graph with orchestrator-worker pattern.
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        intelligence_node = intelligenceAgentNode(self.llm)
        
        # --- Worker Sub-Graph ---
        worker_graph_builder = StateGraph(IntelligenceAgentState)
        worker_graph_builder.add_node("worker_agent", intelligence_node.intelligence_worker_agent)
        worker_graph_builder.add_node("tool_node", intelligence_node.tool_node)
        
        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)
        
        worker_graph = worker_graph_builder.compile()
        
        # --- Main Graph ---
        main_graph_builder = StateGraph(IntelligenceAgentState)
        
        # Add nodes
        main_graph_builder.add_node("data_change_detector", intelligence_node.data_change_detector)
        main_graph_builder.add_node("task_delegator", intelligence_node.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", intelligence_node.prepare_worker_tasks)
        main_graph_builder.add_node(
            "intelligence_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))}
        )
        main_graph_builder.add_node("aggregate_results", intelligence_node.aggregate_results)
        main_graph_builder.add_node("feed_creator", intelligence_node.feed_creator_agent)
        
        # CRITICAL ADAPTER: Convert string feed to domain_insights format
        def format_output(state):
            feed_text = state.get("final_feed", "No intelligence updates.")
            insight = {
                "source_event_id": str(uuid.uuid4()),
                "domain": "intelligence",
                "severity": "medium",
                "summary": feed_text,
                "risk_score": 0.6
            }
            return {"domain_insights": [insight]}
        
        main_graph_builder.add_node("format_output", format_output)
        
        # Wire edges
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "intelligence_workers")
        main_graph_builder.add_edge("intelligence_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        main_graph_builder.add_edge("feed_creator", "format_output")
        main_graph_builder.add_edge("format_output", END)
        
        return main_graph_builder.compile()


# Module-level compilation
print("--- BUILDING INTELLIGENCE AGENT GRAPH ---")
llm = GroqLLM().get_llm()
graph = IntelligenceGraphBuilder(llm).build_graph()
print("✓ Intelligence Agent Graph compiled successfully")