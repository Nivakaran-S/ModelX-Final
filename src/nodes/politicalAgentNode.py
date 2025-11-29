"""
src/nodes/politicalAgentNode.py
COMPLETE - Political Agent Node
Monitors government gazette, parliament minutes, regulatory changes
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.politicalAgentState import PoliticalAgentState
from src.utils.utils import TOOL_MAPPING


class PoliticalAgentNode:
    """
    Political Agent - monitors regulatory and policy changes.
    Implements "Hyper-Localized Political Intel" from your report.
    """
    
    def __init__(self, llm):
        self.llm = llm

    def data_change_detector(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Detects changes in political/regulatory data sources
        """
        print("[POLITICAL] Data Change Detector")
        
        # Placeholder - in production, check gazette RSS or API
        initial_result = {
            "source_tool": "political_probe",
            "raw_content": json.dumps({"status": "monitoring"}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": True,  # Always check for new gazette entries
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    def task_delegator_master_agent(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Plans political monitoring tasks
        """
        print("[POLITICAL] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        # Government Gazette with compliance keywords
        tasks.append({
            "tool_name": "scrape_government_gazette",
            "parameters": {"keywords": ["tax", "import", "export", "regulation", "policy"]},
            "priority": "high"
        })
        
        # Parliament minutes
        tasks.append({
            "tool_name": "scrape_parliament_minutes",
            "parameters": {"keywords": ["bill", "amendment", "budget", "act"]},
            "priority": "high"
        })
        
        print(f"  → Planned {len(tasks)} political monitoring tasks")
        
        return {"generated_tasks": tasks}

    def political_worker_agent(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Worker agent - executes single political monitoring task
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[POLITICAL WORKER] Executing -> {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    def tool_node(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Executes political monitoring tools
        """
        task = state.get("current_task")
        if not task:
            return {}
        
        tool_name = task["tool_name"]
        params = task.get("parameters", {}) or {}
        
        tool_func = TOOL_MAPPING.get(tool_name)
        
        if tool_func:
            try:
                data = tool_func.invoke(params)
                raw = str(data)
            except Exception as e:
                raw = json.dumps({"error": str(e)})
        else:
            raw = json.dumps({"error": f"Tool {tool_name} not found"})
        
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

    def prepare_worker_tasks(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Prepares parallel worker states
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[POLITICAL] Spawning {len(initial_states)} parallel workers")
        
        return {"tasks_for_workers": initial_states}

    def aggregate_results(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Aggregates results from parallel workers
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []
        
        for out in outputs:
            aggregated.extend(out.get("worker_results", []))
        
        print(f"[POLITICAL] Aggregated {len(aggregated)} results")
        
        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated
        }

    def feed_creator_agent(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Creates political intelligence feed
        """
        print("[POLITICAL] Feed Creator")
        
        all_results = state.get("worker_results", []) or []
        
        gazette_items = []
        parliament_items = []
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            content = r.get("raw_content", "")
            
            if "gazette" in source_tool:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        gazette_items.extend(data[:5])  # Top 5
                except:
                    pass
            elif "parliament" in source_tool:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        parliament_items.extend(data[:5])
                except:
                    pass
        
        gazette_text = "\n".join([f"• {item.get('title', 'N/A')}" for item in gazette_items]) if gazette_items else "No new gazette entries"
        parliament_text = "\n".join([f"• {item.get('title', 'N/A')}" for item in parliament_items]) if parliament_items else "No new parliamentary minutes"
        
        bulletin = f"""🇱🇰 POLITICAL INTELLIGENCE FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

📜 GOVERNMENT GAZETTE
{gazette_text}

🏛️ PARLIAMENT MINUTES
{parliament_text}

⚠️ COMPLIANCE ALERTS
Review latest gazette entries for regulatory changes affecting:
- Import/Export regulations
- Tax policy updates
- Labor law amendments

Source: Government of Sri Lanka
"""
        
        print("  ✓ Feed created")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin]
        }