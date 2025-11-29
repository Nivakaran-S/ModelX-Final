"""
src/nodes/intelligenceAgentNode.py
COMPLETE - Intelligence Agent Node
Handles brand monitoring, competitive intelligence, entity tracking
Maps to "Market Intelligence Agent (Brand Intel)" from your report
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.intelligenceAgentState import IntelligenceAgentState
from src.utils.utils import TOOL_MAPPING


class intelligenceAgentNode:
    """
    Intelligence Agent - on-demand brand and entity monitoring.
    Uses "Pull" mechanism as described in your hybrid engine architecture.
    """
    
    def __init__(self, llm):
        self.llm = llm

    def data_change_detector(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Intelligence agent runs on-demand, not on change detection
        """
        print("[INTELLIGENCE] Data Change Detector (On-Demand Mode)")
        
        initial_result = {
            "source_tool": "intelligence_probe",
            "raw_content": json.dumps({"status": "standby"}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": False,  # On-demand only
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    def task_delegator_master_agent(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Plans intelligence gathering tasks
        """
        print("[INTELLIGENCE] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        # Brand monitoring via local news
        tasks.append({
            "tool_name": "scrape_local_news",
            "parameters": {"keywords": ["company", "brand", "business"], "max_articles": 20},
            "priority": "normal"
        })
        
        # Entity tracking via Reddit
        tasks.append({
            "tool_name": "scrape_reddit",
            "parameters": {"keywords": ["Sri Lankan company", "business"], "limit": 10},
            "priority": "normal"
        })
        
        print(f"  → Planned {len(tasks)} intelligence tasks")
        
        return {"generated_tasks": tasks}

    def intelligence_worker_agent(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Worker agent - executes single intelligence task
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[INTELLIGENCE WORKER] Executing -> {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    def tool_node(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Executes intelligence gathering tools
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

    def prepare_worker_tasks(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Prepares parallel worker states
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[INTELLIGENCE] Spawning {len(initial_states)} parallel workers")
        
        return {"tasks_for_workers": initial_states}

    def aggregate_results(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Aggregates results from parallel workers
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []
        
        for out in outputs:
            aggregated.extend(out.get("worker_results", []))
        
        print(f"[INTELLIGENCE] Aggregated {len(aggregated)} results")
        
        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated
        }

    def feed_creator_agent(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Creates intelligence report with brand mentions and entity tracking
        """
        print("[INTELLIGENCE] Feed Creator")
        
        all_results = state.get("worker_results", []) or []
        
        brand_mentions = []
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            content = r.get("raw_content", "")
            
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data:
                        if "company" in str(item).lower() or "brand" in str(item).lower():
                            brand_mentions.append(item)
            except:
                pass
        
        mentions_text = "\n".join([
            f"• {mention.get('headline') or mention.get('title', 'N/A')[:80]}..." 
            for mention in brand_mentions[:10]
        ]) if brand_mentions else "No brand mentions detected"
        
        bulletin = f"""🇱🇰 MARKET INTELLIGENCE FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

🎯 BRAND MENTIONS
{mentions_text}

📊 ENTITY TRACKING
Monitoring mentions of tracked entities across:
- Local news media
- Social media platforms
- Public forums

⚠️ COMPETITIVE INTELLIGENCE
- Track competitor announcements
- Monitor industry trends
- Identify market opportunities

This feed supports B2B due diligence and strategic planning.

Source: Aggregated Public Sources
"""
        
        print("  ✓ Feed created")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin]
        }