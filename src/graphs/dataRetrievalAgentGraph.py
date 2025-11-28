import operator
import json
import uuid
from datetime import datetime
from typing import Annotated, List, Literal, Dict, Any, Optional

# LangChain / LangGraph Imports
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from src.llms.groqllm import GroqLLM
from src.states.dataRetrievalAgentState import DataRetrievalAgentState
from src.nodes.dataRetrievalAgentNode import DataRetrievalAgentNode


class DataRetrievalAgentGraph(DataRetrievalAgentNode):
    def __init__(self, llm):
        super().__init__(llm)
        self.llm = llm

    def prepare_worker_tasks(self, state: DataRetrievalAgentState) -> dict:
        """Prepares the list of tasks for parallel execution by the worker graph."""
        tasks = state.generated_tasks
        initial_states = [{"generated_tasks": [task]} for task in tasks]
        return {"tasks_for_workers": initial_states}

    def create_worker_graph(self):
        """Creates a self-contained graph for a single worker agent that can use tools."""
        worker_graph_builder = StateGraph(DataRetrievalAgentState)
        
        worker_graph_builder.add_node("worker_agent", self.worker_agent_node)
        worker_graph_builder.add_node("tool_node", self.tool_node)

        worker_graph_builder.set_entry_point("worker_agent")
        worker_graph_builder.add_edge("worker_agent", "tool_node")
        worker_graph_builder.add_edge("worker_agent", END)
        
        return worker_graph_builder.compile()

    def aggregate_results(self, state: DataRetrievalAgentState) -> dict:
        """Aggregates results from parallel worker runs."""
        worker_outputs = getattr(state, 'worker', [])
        new_results = []
        for output in worker_outputs:
            # The output from a mapped graph is a dictionary.
            if "worker_results" in output and output["worker_results"]:
                new_results.extend(output["worker_results"])
        
        return {
            "worker_results": new_results, # Appends to the main log
            "latest_worker_results": new_results # Overwrites with the latest batch
        }

    def build_data_retrieval_agent_graph(self):
        worker_graph = self.create_worker_graph()

        workflow = StateGraph(DataRetrievalAgentState)

        # Add Nodes
        workflow.add_node("master_delegator", self.master_agent_node)
        workflow.add_node("prepare_worker_tasks", self.prepare_worker_tasks)
        # The "worker" node is a lambda that invokes the mapped worker graph
        workflow.add_node(
            "worker",
            lambda state: {"worker": worker_graph.map().invoke(state.tasks_for_workers)},
        )
        workflow.add_node("aggregate_results", self.aggregate_results)
        workflow.add_node("classifier_agent", self.classifier_agent_node)

        # Edges:
        workflow.set_entry_point("master_delegator")
        workflow.add_edge("master_delegator", "prepare_worker_tasks")
        workflow.add_edge("prepare_worker_tasks", "worker")
        workflow.add_edge("worker", "aggregate_results")
        workflow.add_edge("aggregate_results", "classifier_agent")
        workflow.add_edge("classifier_agent", END)

        return workflow.compile()

# Compile graph
llm = GroqLLM().get_llm()
graph_builder = DataRetrievalAgentGraph(llm)
graph = graph_builder.build_data_retrieval_agent_graph()
print("Data Retrieval Agent Graph built successfully.")





