import json
import uuid
from typing import List, Literal
from langchain_core.messages import HumanMessage, SystemMessage, get_buffer_string
from langgraph.graph import END
from src.states.intelligenceAgentState import IntelligenceAgentState,  ClassifiedEvent
from src.utils.prompts import MASTER_AGENT_SYSTEM_PROMPT, MASTER_AGENT_HUMAN_PROMPT
from src.utils.utils import get_today_str, TOOL_MAPPING, tool_dmc_alerts, tool_weather_nowcast
from typing_extensions import Dict, Any
from datetime import datetime

class intelligenceAgentNode:
    def __init__(self, llm):
        self.llm = llm 

        
    def data_change_detector(self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        DATA CHANGE DETECTOR / UPDATED DATA FILTER AGENT

        - Probes the DMC page quickly.
        - Compares hash with previous run.
        - Flags whether new/changed alerts are likely.
        - NOTE: It does NOT block execution; it just annotates `change_detected`
        so downstream nodes (e.g., feed creator) can highlight it.
        """
        print("--- [DATA CHANGE DETECTOR] ---")

        # Lightweight probe: reuse full DMC scraper here for simplicity
        dmc_data = tool_dmc_alerts()
        raw_json = json.dumps(dmc_data, sort_keys=True)
        current_hash = hash(raw_json)
        previous_hash = state.get("last_alerts_hash")

        change = previous_hash is None or current_hash != previous_hash
        if change:
            print("   → Change detected in DMC alerts.")
        else:
            print("   → No change detected in DMC alerts.")

        # We also push this as an initial worker result so feed creator always
        # sees the latest DMC content, even before orchestrated tools.
        initial_result = {
            "source_tool": "dmc_alerts_probe",
            "raw_content": raw_json,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return {
            "change_detected": change,
            "last_alerts_hash": current_hash,
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result],
        }


    def task_delegator_master_agent(
        self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        TASK DELEGATOR – MASTER AGENT

        - Always schedules both tools:
            * Weather nowcast for several key cities.
            * DMC alerts scraper as a full tool call.
        - This is the entry into the orchestrator-worker workflow box.
        """
        print("--- [TASK DELEGATOR / MASTER AGENT] ---")

        tasks: List[Dict[str, Any]] = []

        # DMC alerts tool (full scrape)
        tasks.append(
            {
                "tool_name": "dmc_alerts",
                "parameters": {},
                "priority": "high",
            }
        )

        # Weather nowcast for multiple cities
        for loc in ["Colombo", "Kandy", "Galle", "Jaffna"]:
            tasks.append(
                {
                    "tool_name": "weather_nowcast",
                    "parameters": {"location": loc},
                    "priority": "normal",
                }
            )

        print(f"   → Planned {len(tasks)} tasks for Meteorological Worker Agents.")

        return {"generated_tasks": tasks}


    def meteorological_worker_agent(
            self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        METEOROLOGICAL WORKER AGENT

        - Pops a single task from `generated_tasks` for this worker instance.
        - In the mapped worker graph, each instance handles exactly one task.
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            print("--- [WORKER] No task available ---")
            return {}

        task = tasks[0]
        remaining = tasks[1:]

        print(f"--- [WORKER] Dispatching task -> {task['tool_name']} ---")

        return {
            "current_task": task,
            "generated_tasks": remaining,
        }


    def tool_node(
            self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        TOOL NODE

        - Executes the tool specified by `current_task`.
        - This corresponds to the 'ToolNode' in the diagram, with
        arrows to 'Weather Nowcast' and 'DMC alert scraper'.
        """
        task = state.get("current_task")
        if not task:
            print("--- [TOOL NODE] No current task ---")
            return {}

        tool_name = task["tool_name"]
        params = task.get("parameters", {}) or {}

        print(f"--- [TOOL NODE] Executing tool -> {tool_name} ---")

        if tool_name == "dmc_alerts":
            data = tool_dmc_alerts()
        elif tool_name == "weather_nowcast":
            data = tool_weather_nowcast(**params)
        else:
            data = {"error": f"Unknown tool: {tool_name}", "tool_name": tool_name}

        raw = json.dumps(data)
        result = {
            "source_tool": tool_name,
            "raw_content": raw,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return {
            "worker_results": [result],
            "latest_worker_results": [result],
            "current_task": None,
        }


    def prepare_worker_tasks(
        self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        Prepares the list of tasks for parallel worker execution.

        - Each entry in `tasks_for_workers` is an initial state for a worker graph
        that will run `meteorological_worker_agent` + `tool_node`.
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]

        print(
            f"--- [PREPARE WORKER TASKS] Spawning {len(initial_states)} "
            "parallel Meteorological Worker Agents ---"
        )

        return {"tasks_for_workers": initial_states}


    def aggregate_results(
            self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        Aggregates results from all parallel workers.

        - `state["worker"]` contains the outputs of each mapped worker run.
        - We flatten them into `worker_results` and set `latest_worker_results`
        for downstream use.
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []

        for out in outputs:
            aggregated.extend(out.get("worker_results", []))

        print(f"--- [AGGREGATE RESULTS] Aggregated {len(aggregated)} worker results ---")

        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated,
        }


    def feed_creator_agent(
            self,
        state: IntelligenceAgentState,
    ) -> Dict[str, Any]:
        """
        FEED CREATOR AGENT

        - Consumes all `worker_results` (DMC + nowcasts).
        - Builds a consolidated meteorological feed and stores it in:
            * `final_feed` – latest feed
            * `feed_history` – append-only history
        """
        print("--- [FEED CREATOR AGENT] ---")

        all_results = state.get("worker_results", []) or []

        latest_dmc_text = "No DMC alerts available."
        nowcast_blocks: List[str] = []

        # Prefer full-tool DMC result if available; otherwise use probe.
        dmc_full = None
        dmc_probe = None

        for r in all_results:
            source_tool = r.get("source_tool", "")
            try:
                data = json.loads(r.get("raw_content", "{}"))
            except Exception:
                data = {}

            if source_tool == "dmc_alerts":
                dmc_full = data
            elif source_tool == "dmc_alerts_probe":
                dmc_probe = data
            elif source_tool == "weather_nowcast":
                loc = data.get("location", "Unknown")
                text = data.get("forecast", "") or "No forecast text."
                text = text[:800]  # keep reasonable size per location
                nowcast_blocks.append(f"• {loc}:\n{text}")

        use_dmc = dmc_full or dmc_probe
        if use_dmc:
            alerts = use_dmc.get("alerts", [])
            latest_dmc_text = "\n\n".join(alerts) if alerts else "No alerts listed."

        forecast_section = (
            "\n\n".join(nowcast_blocks) if nowcast_blocks else "No nowcast data available."
        )

        change_flag = state.get("change_detected", False)
        change_line = (
            "Recent change detected in severe weather alerts.\n"
            if change_flag
            else "No significant change detected in severe weather alerts since last run.\n"
        )

        bulletin = f"""🇱🇰 SRI LANKA METEOROLOGICAL FEED
    {datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

    {change_line}
    ⚠️ DMC ALERTS / ADVISORIES
    {latest_dmc_text}

    🌤️ WEATHER NOWCAST (Key Locations)
    {forecast_section}

    Source: Department of Meteorology Sri Lanka (meteo.gov.lk)
    """

        bulletin = bulletin.strip()

        print("   → Feed created.")

        return {
            "final_feed": bulletin,
            "feed_history": [bulletin],
        }
