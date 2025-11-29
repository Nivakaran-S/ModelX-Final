"""
src/nodes/meteorologicalAgentNode.py
COMPLETE - Meteorological Agent Node
Monitors weather alerts, DMC warnings, forecasts
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.meteorologicalAgentState import MeteorologicalAgentState
from src.utils.utils import tool_dmc_alerts, tool_weather_nowcast


class MeteorologicalAgentNode:
    """
    Meteorological Agent - monitors weather and disaster alerts.
    Implements the "Operational Risk Radar" weather component from your report.
    """
    
    def __init__(self, llm):
        self.llm = llm

    # =========================================================================
    # 1. DATA CHANGE DETECTOR
    # =========================================================================
    
    def data_change_detector(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        DATA CHANGE DETECTOR
        
        Probes DMC alerts and compares with previous run.
        Sets change_detected flag if new alerts appeared.
        """
        print("[WEATHER] Data Change Detector")
        
        dmc_data = tool_dmc_alerts()
        raw_json = json.dumps(dmc_data, sort_keys=True)
        current_hash = hash(raw_json)
        previous_hash = state.get("last_alerts_hash")
        
        change = previous_hash is None or current_hash != previous_hash
        
        if change:
            print("  ✓ New weather alerts detected")
        else:
            print("  - No change in alerts")
        
        initial_result = {
            "source_tool": "dmc_alerts_probe",
            "raw_content": raw_json,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": change,
            "last_alerts_hash": current_hash,
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    # =========================================================================
    # 2. TASK DELEGATOR
    # =========================================================================
    
    def task_delegator_master_agent(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        TASK DELEGATOR - Plans weather monitoring tasks
        
        Always schedules:
        - DMC alerts scraper
        - Weather nowcast for key cities
        """
        print("[WEATHER] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        # DMC alerts
        tasks.append({
            "tool_name": "dmc_alerts",
            "parameters": {},
            "priority": "high"
        })
        
        # Weather nowcast for multiple cities
        for city in ["Colombo", "Kandy", "Galle", "Jaffna"]:
            tasks.append({
                "tool_name": "weather_nowcast",
                "parameters": {"location": city},
                "priority": "normal"
            })
        
        print(f"  → Planned {len(tasks)} weather monitoring tasks")
        
        return {"generated_tasks": tasks}

    # =========================================================================
    # 3. WORKER AGENT
    # =========================================================================
    
    def meteorological_worker_agent(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        WORKER AGENT - Pops and executes single task
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[WEATHER WORKER] Executing -> {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    # =========================================================================
    # 4. TOOL NODE
    # =========================================================================
    
    def tool_node(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        TOOL NODE - Executes weather monitoring tools
        """
        task = state.get("current_task")
        if not task:
            return {}
        
        tool_name = task["tool_name"]
        params = task.get("parameters", {}) or {}
        
        if tool_name == "dmc_alerts":
            data = tool_dmc_alerts()
        elif tool_name == "weather_nowcast":
            data = tool_weather_nowcast(**params)
        else:
            data = {"error": f"Unknown tool: {tool_name}"}
        
        raw = json.dumps(data)
        result = {
            "source_tool": tool_name,
            "raw_content": raw,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "worker_results": [result],
            "latest_worker_results": [result],
            "current_task": None
        }

    # =========================================================================
    # 5. PREPARE WORKER TASKS
    # =========================================================================
    
    def prepare_worker_tasks(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        Prepares parallel worker execution states
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[WEATHER] Spawning {len(initial_states)} parallel workers")
        
        return {"tasks_for_workers": initial_states}

    # =========================================================================
    # 6. AGGREGATE RESULTS
    # =========================================================================
    
    def aggregate_results(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        Aggregates results from parallel workers
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []
        
        for out in outputs:
            aggregated.extend(out.get("worker_results", []))
        
        print(f"[WEATHER] Aggregated {len(aggregated)} results")
        
        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated
        }

    # =========================================================================
    # 7. FEED CREATOR
    # =========================================================================
    
    def feed_creator_agent(self, state: MeteorologicalAgentState) -> Dict[str, Any]:
        """
        FEED CREATOR - Builds human-readable weather bulletin
        """
        print("[WEATHER] Feed Creator")
        
        all_results = state.get("worker_results", []) or []
        
        latest_dmc_text = "No DMC alerts available."
        nowcast_blocks: List[str] = []
        
        dmc_full = None
        dmc_probe = None
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            try:
                data = json.loads(r.get("raw_content", "{}"))
            except:
                data = {}
            
            if source_tool == "dmc_alerts":
                dmc_full = data
            elif source_tool == "dmc_alerts_probe":
                dmc_probe = data
            elif source_tool == "weather_nowcast":
                loc = data.get("location", "Unknown")
                text = data.get("forecast", "")[:800]
                nowcast_blocks.append(f"• {loc}:\n{text}")
        
        use_dmc = dmc_full or dmc_probe
        if use_dmc:
            alerts = use_dmc.get("alerts", [])
            latest_dmc_text = "\n\n".join(alerts) if alerts else "No alerts listed."
        
        forecast_section = "\n\n".join(nowcast_blocks) if nowcast_blocks else "No nowcast data."
        
        change_flag = state.get("change_detected", False)
        change_line = "⚠️ NEW ALERTS DETECTED\n" if change_flag else ""
        
        bulletin = f"""🇱🇰 METEOROLOGICAL FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

{change_line}
📍 DMC ALERTS / ADVISORIES
{latest_dmc_text}

🌤️ WEATHER NOWCAST
{forecast_section}

Source: Department of Meteorology Sri Lanka
"""
        
        print("  ✓ Feed created")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin]
        }