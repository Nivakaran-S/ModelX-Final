import json
import uuid
from typing import List, Literal
from langchain_core.messages import HumanMessage, SystemMessage, get_buffer_string
from langgraph.graph import END
from src.states.dataRetrievalAgentState import DataRetrievalAgentState, ScrapingTask, RawScrapedData, ClassifiedEvent
from src.utils.prompts import MASTER_AGENT_SYSTEM_PROMPT, MASTER_AGENT_HUMAN_PROMPT
from src.utils.utils import get_today_str, TOOL_MAPPING

# Import your actual tools logic here
# from src.tools.tools import TOOL_REGISTRY 

class DataRetrievalAgentNode:
    def __init__(self, llm):
        self.llm = llm 

        
    def master_agent_node(self, state: DataRetrievalAgentState):
        """
        TASK DELEGATOR MASTER AGENT
        Decides which tools to run based on history and context.
        """
        print("--- 1. MASTER AGENT: Planning Tasks ---")

        completed_tools = [r.source_tool for r in state.worker_results]

        system_prompt = f"""
    You are the Master Data Retrieval Agent for a government-focused monitoring system.

    You have access to these tools (via Worker + ToolNode): {list(TOOL_MAPPING.keys())}

    Your job:
    - Decide which tools to run now to keep the system updated.
    - Avoid re-running the same tools repeatedly if they were just executed.
    - Prefer a mix of:
    - social media (scrape_linkedin, scrape_instagram, scrape_facebook, scrape_reddit, scrape_twitter)
    - official sources (scrape_government_gazette, scrape_parliament_minutes, scrape_train_schedule)
    - market and news (scrape_cse_stock_data, scrape_local_news)

    Input context:
    - Previously planned tasks: {state.previous_tasks}
    - Already completed in this run: {completed_tools}

    You may also specify keywords to focus on topics like:
    - "election", "policy", "budget", "strike", "inflation", "fuel", "railway", "protest"

    Respond ONLY with valid JSON representing a list of tasks.
    Schema:
    [
    {{
        "tool_name": "<one of {list(TOOL_MAPPING.keys())}>",
        "parameters": {{...}},   // optional tool params (include keywords when useful)
        "priority": "high" | "normal"
    }},
    ...
    ]

    If no task is needed, return [].
    """

        parsed_tasks: List[ScrapingTask] = []

        try:
            
            response = self.llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content="Plan the next scraping wave for routine monitoring."
                    ),
                ]
            )
            raw = response.content
            suggested = json.loads(raw)

            if isinstance(suggested, dict):
                suggested = [suggested]

            for item in suggested:
                try:
                    task = ScrapingTask(**item)
                    parsed_tasks.append(task)
                except Exception as e:
                    print(f"[MASTER] Failed to parse task item {item}: {e}")
                    continue
        except Exception as e:
            print(f"[MASTER] LLM planning failed, falling back. Reason: {e}")

        # Fallback plan if LLM fails or returns nothing usable
        if not parsed_tasks and not state.previous_tasks:
            parsed_tasks = [
                ScrapingTask(
                    tool_name="scrape_local_news",
                    parameters={"keywords": ["stock", "market", "budget"]},
                    priority="high",
                ),
                ScrapingTask(
                    tool_name="scrape_cse_stock_data",
                    parameters={"symbol": "ASPI"},
                    priority="high",
                ),
                ScrapingTask(
                    tool_name="scrape_government_gazette",
                    parameters={"keywords": ["tax", "import", "policy"]},
                    priority="normal",
                ),
                ScrapingTask(
                    tool_name="scrape_parliament_minutes",
                    parameters={"keywords": ["budget", "bill", "amendment"]},
                    priority="normal",
                ),
                ScrapingTask(
                    tool_name="scrape_train_schedule",
                    parameters={"keyword": "Colombo"},
                    priority="normal",
                ),
                ScrapingTask(
                    tool_name="scrape_reddit",
                    parameters={"keywords": ["Sri Lanka", "economy"], "limit": 10},
                    priority="normal",
                ),
            ]

        return {
            "generated_tasks": parsed_tasks,
            "previous_tasks": [t.tool_name for t in parsed_tasks],
        }


    def worker_agent_node(self, state: DataRetrievalAgentState):
        """
        DATA RETRIEVAL WORKER AGENT
        Pops the next task from the queue and prepares it for the ToolNode.
        """
        if not state.generated_tasks:
            print("--- 2. WORKER: No tasks in queue ---")
            return {}

        # Pop next task (FIFO)
        current_task = state.generated_tasks[0]
        remaining = state.generated_tasks[1:]

        print(f"--- 2. WORKER: Dispatching task -> {current_task.tool_name} ---")

        return {
            "generated_tasks": remaining,
            "current_task": current_task,
        }


    def tool_node(self, state: DataRetrievalAgentState):
        """
        TOOL NODE
        Executes the tool specified by `current_task` and records the raw result.
        """
        current_task = state.current_task
        if current_task is None:
            print("--- 2b. TOOL NODE: No active task ---")
            return {}

        print(f"--- 2b. TOOL NODE: Executing tool -> {current_task.tool_name} ---")

        tool_func = TOOL_MAPPING.get(current_task.tool_name)
        if tool_func is None:
            output = "Tool not found in registry."
            status: Literal["success", "failed"] = "failed"
        else:
            try:
                # LangChain tools expect kwargs
                output = tool_func.invoke(current_task.parameters or {})
                status = "success"
            except Exception as e:
                output = f"Error: {str(e)}"
                status = "failed"

        result = RawScrapedData(
            source_tool=current_task.tool_name,
            raw_content=str(output),
            status=status,
        )

        return {
            "current_task": None,       # task processed
            "worker_results": [result], # append result
        }


    def classifier_agent_node(self, state: DataRetrievalAgentState):
        """
        DATA CLASSIFIER AGENT
        Analyzes a batch of worker results, summarizes them, and classifies them for a specialized agent.
        """
        if not state.latest_worker_results:
            print("--- 3. CLASSIFIER: No new worker results to process ---")
            return {}

        print(f"--- 3. CLASSIFIER: Processing {len(state.latest_worker_results)} new results ---")

        agent_categories = [
            "social_agent", 
            "economical_agent", 
            "political_agent", 
            "mobility_agent", 
            "meteorological_agent", 
            "entity_tracking_agent"
        ]

        system_prompt = f"""
You are a data classification expert for a sophisticated AI monitoring system.
Your task is to analyze scraped data and route it to the correct specialized agent.

The available agents are:
- social_agent: Handles information from social media platforms (Twitter, Reddit, etc.). Focuses on public sentiment, trends, and discussions.
- economical_agent: Analyzes financial and economic data, such as stock market updates, economic news, and budget announcements.
- political_agent: Processes information related to government activities, policies, legislation, and political events (e.g., from government gazettes, parliament minutes).
- mobility_agent: Tracks data related to transportation and logistics, such as train schedules, traffic updates, or port activity.
- meteorological_agent: Manages weather-related information and forecasts.
- entity_tracking_agent: Monitors for mentions of specific persons, organizations, or topics of interest across all data sources.

Based on the provided data, perform two tasks:
1.  Write a concise, one-sentence summary of the key event or signal in the data.
2.  Choose the single most appropriate agent from the list above to handle this information.

Respond with a valid JSON object with two keys: "summary" and "target_agent".
Example:
{{
  "summary": "The All Share Price Index (ASPI) increased by 5.8 points today.",
  "target_agent": "economical_agent"
}}
"""
        
        all_classified_events = []
        for latest_result in state.latest_worker_results:
            try:
                response = self.llm.invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Data Source: {latest_result.source_tool}\n\nContent:\n{latest_result.raw_content}"),
                    ]
                )
                
                result_json = json.loads(response.content)
                summary_text = result_json.get("summary", "No summary provided.")
                target_agent = result_json.get("target_agent", "general_news_agent")

                if target_agent not in agent_categories:
                    print(f"[CLASSIFIER] LLM returned an invalid agent '{target_agent}'. Falling back.")
                    target_agent = "general_news_agent"

            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"[CLASSIFIER] LLM classification failed for item from {latest_result.source_tool}: {e}. Falling back to basic classification.")
                source = latest_result.source_tool
                if "stock" in source or "market" in source or "economy" in source:
                    target_agent = "economical_agent"
                elif "gazette" in source or "parliament" in source or "policy" in source:
                    target_agent = "political_agent"
                elif "train_schedule" in source:
                    target_agent = "mobility_agent"
                elif any(s in source for s in ["linkedin", "instagram", "facebook", "reddit", "twitter"]):
                    target_agent = "social_agent"
                else:
                    target_agent = "general_news_agent"

                summary_text = f"Processed data from {source}: {latest_result.raw_content[:180]}..."

            classified = ClassifiedEvent(
                event_id=str(uuid.uuid4()),
                content_summary=summary_text,
                target_agent=target_agent,
                confidence_score=0.95,
            )
            all_classified_events.append(classified)

        return {
            "classified_buffer": all_classified_events,
            "latest_worker_results": [] # Clear the temporary field
        }


    # ==========================================
    # 5. CONDITIONAL EDGES
    # ==========================================

    def route_next_step(self, state: DataRetrievalAgentState):
        """
        Determines if we loop back to Worker or finish.
        """
        if len(state.generated_tasks) > 0:
            return "worker_agent"
        return END