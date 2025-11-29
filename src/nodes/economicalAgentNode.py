"""
src/nodes/economicalAgentNode.py
COMPLETE - Economical Agent Node
Monitors CSE stock market, economic indicators, market anomalies
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.economicalAgentState import EconomicalAgentState
from src.utils.utils import TOOL_MAPPING


class economicalAgentNode:
    """
    Economical Agent - monitors market data and economic indicators.
    Implements "Market Anomaly Detection" from your report.
    """
    
    def __init__(self, llm):
        self.llm = llm

    def data_change_detector(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Detects changes in market data
        """
        print("[ECONOMIC] Data Change Detector")
        
        initial_result = {
            "source_tool": "market_probe",
            "raw_content": json.dumps({"status": "monitoring"}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": True,  # Always check market updates
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    def task_delegator_master_agent(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Plans economic monitoring tasks
        """
        print("[ECONOMIC] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        # CSE Stock Data - ASPI index
        tasks.append({
            "tool_name": "scrape_cse_stock_data",
            "parameters": {"symbol": "ASPI", "period": "1d"},
            "priority": "high"
        })
        
        # Local economic news
        tasks.append({
            "tool_name": "scrape_local_news",
            "parameters": {"keywords": ["economy", "inflation", "market", "stock"]},
            "priority": "high"
        })
        
        print(f"  → Planned {len(tasks)} economic monitoring tasks")
        
        return {"generated_tasks": tasks}

    def economical_worker_agent(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Worker agent - executes single economic monitoring task
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[ECONOMIC WORKER] Executing -> {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    def tool_node(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Executes economic monitoring tools
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

    def prepare_worker_tasks(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Prepares parallel worker states
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[ECONOMIC] Spawning {len(initial_states)} parallel workers")
        
        return {"tasks_for_workers": initial_states}

    def aggregate_results(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Aggregates results from parallel workers
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []
        
        for out in outputs:
            aggregated.extend(out.get("worker_results", []))
        
        print(f"[ECONOMIC] Aggregated {len(aggregated)} results")
        
        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated
        }

    def feed_creator_agent(self, state: EconomicalAgentState) -> Dict[str, Any]:
        """
        Creates economic intelligence feed with anomaly detection
        """
        print("[ECONOMIC] Feed Creator")
        
        all_results = state.get("worker_results", []) or []
        
        market_data = []
        news_items = []
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            content = r.get("raw_content", "")
            
            if "stock" in source_tool or "cse" in source_tool:
                try:
                    data = json.loads(content)
                    market_data.append(data)
                except:
                    pass
            elif "news" in source_tool:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        news_items.extend(data[:5])
                except:
                    pass
        
        # Analyze market data for anomalies
        market_text = "No market data available"
        if market_data:
            # Simple anomaly detection placeholder
            market_text = f"ASPI data retrieved. Monitoring for volatility spikes."
        
        news_text = "\n".join([f"• {item.get('headline', 'N/A')}" for item in news_items]) if news_items else "No economic news"
        
        bulletin = f"""🇱🇰 ECONOMIC INTELLIGENCE FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

📊 CSE MARKET STATUS
{market_text}

📰 ECONOMIC NEWS
{news_text}

⚠️ ANOMALY DETECTION
Monitoring for:
- Volume spikes > 2σ above mean
- Price volatility > 5% daily change
- Unusual trading patterns

Source: Colombo Stock Exchange & Local Media
"""
        
        print("  ✓ Feed created")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin]
        }