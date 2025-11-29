"""
src/graphs/socialAgentGraph.py
COMPLETE - Social Agent Graph Builder
"""
import uuid
from langgraph.graph import StateGraph, END
from src.states.socialAgentState import SocialAgentState
from src.nodes.socialAgentNode import SocialAgentNode
from src.llms.groqllm import GroqLLM


class SocialGraphBuilder:
    """
    Builds the Social Agent graph with orchestrator-worker pattern.
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def build_graph(self):
        social_node = SocialAgentNode(self.llm)
        
        # --- Worker Sub-Graph ---
        worker_graph_builder = StateGraph(SocialAgentState)
        worker_graph_builder.add_node("worker_agent", social_node.social_worker_agent)
        worker_graph_builder.add_node("tool_node", social_node.tool_node)
        
        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("tool_node", END)
        
        worker_graph = worker_graph_builder.compile()
        
        # --- Main Graph ---
        main_graph_builder = StateGraph(SocialAgentState)
        
        # Add nodes
        main_graph_builder.add_node("data_change_detector", social_node.data_change_detector)
        main_graph_builder.add_node("task_delegator", social_node.task_delegator_master_agent)
        main_graph_builder.add_node("prepare_worker_tasks", social_node.prepare_worker_tasks)
        main_graph_builder.add_node(
            "social_workers",
            lambda s: {"worker": worker_graph.map().invoke(s.get("tasks_for_workers", []))}
        )
        main_graph_builder.add_node("aggregate_results", social_node.aggregate_results)
        main_graph_builder.add_node("feed_creator", social_node.feed_creator_agent)
        
        # CRITICAL ADAPTER: Convert string feed to domain_insights format
        def format_output(state):
            feed_text = state.get("final_feed", "No social media updates.")
            insight = {
                "source_event_id": str(uuid.uuid4()),
                "domain": "social",
                "severity": "medium",
                "summary": feed_text,
                "risk_score": 0.5
            }
            return {"domain_insights": [insight]}
        
        main_graph_builder.add_node("format_output", format_output)
        
        # Wire edges
        main_graph_builder.set_entry_point("data_change_detector")
        main_graph_builder.add_edge("data_change_detector", "task_delegator")
        main_graph_builder.add_edge("task_delegator", "prepare_worker_tasks")
        main_graph_builder.add_edge("prepare_worker_tasks", "social_workers")
        main_graph_builder.add_edge("social_workers", "aggregate_results")
        main_graph_builder.add_edge("aggregate_results", "feed_creator")
        main_graph_builder.add_edge("feed_creator", "format_output")
        main_graph_builder.add_edge("format_output", END)
        
        return main_graph_builder.compile()


# Module-level compilation
print("--- BUILDING SOCIAL AGENT GRAPH ---")
llm = GroqLLM().get_llm()
graph = SocialGraphBuilder(llm).build_graph()
print("✓ Social Agent Graph compiled successfully")