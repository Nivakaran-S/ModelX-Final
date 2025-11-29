"""
src/nodes/economicalAgentNode.py
FIXED - Proper domain_insights output for Mother Graph
"""
import json
import uuid
import statistics
from typing import List, Dict, Any
from datetime import datetime
from src.states.economicalAgentState import EconomicalAgentState
from src.utils.utils import TOOL_MAPPING


class economicalAgentNode:
    def __init__(self, llm):
        self.llm = llm

    def data_change_detector(self, state: EconomicalAgentState) -> Dict[str, Any]:
        print("[ECONOMIC] Data Change Detector")
        
        initial_result = {
            "source_tool": "market_probe",
            "raw_content": json.dumps({"status": "monitoring"}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": True,
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    def task_delegator_master_agent(self, state: EconomicalAgentState) -> Dict[str, Any]:
        print("[ECONOMIC] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        tasks.append({
            "tool_name": "scrape_cse_stock_data",
            "parameters": {"symbol": "ASPI", "period": "5d"},
            "priority": "high"
        })
        
        tasks.append({
            "tool_name": "scrape_local_news",
            "parameters": {"keywords": ["economy", "inflation", "market", "imf", "investment"]},
            "priority": "high"
        })
        
        print(f"  → Planned {len(tasks)} tasks")
        return {"generated_tasks": tasks}

    def economical_worker_agent(self, state: EconomicalAgentState) -> Dict[str, Any]:
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[ECONOMIC WORKER] → {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    def tool_node(self, state: EconomicalAgentState) -> Dict[str, Any]:
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
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[ECONOMIC] Spawning {len(initial_states)} workers")
        
        return {"tasks_for_workers": initial_states}

    def aggregate_results(self, state: EconomicalAgentState) -> Dict[str, Any]:
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
        CRITICAL FIX: Returns domain_insights array instead of final_feed string
        """
        print("[ECONOMIC] Feed Creator - Analyzing Market")
        
        all_results = state.get("worker_results", []) or []
        
        market_data = []
        news_items = []
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            content = r.get("raw_content", "")
            
            if "stock" in source_tool or "cse" in source_tool:
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "records" in parsed:
                        market_data.extend(parsed["records"])
                except:
                    pass
            elif "news" in source_tool:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        news_items.extend(data[:5])
                except:
                    pass
        
        insights_list = []
        
        # Technical Analysis
        if market_data and len(market_data) >= 5:
            try:
                closes = [float(d.get('Close', d.get('close', 0))) for d in market_data if 'Close' in d or 'close' in d]
                
                if len(closes) >= 5:
                    current_price = closes[-1]
                    sma_5 = statistics.mean(closes[-5:])
                    percent_diff = ((current_price - sma_5) / sma_5) * 100
                    
                    if percent_diff > 1.5:
                        impact = "opportunity"
                        severity = "medium"
                        summary = f"📈 BULLISH SIGNAL: ASPI Index {percent_diff:.2f}% above 5-day SMA. Positive market momentum detected."
                    elif percent_diff < -1.5:
                        impact = "risk"
                        severity = "medium"
                        summary = f"📉 BEARISH SIGNAL: ASPI Index {abs(percent_diff):.2f}% below 5-day SMA. Market contraction detected."
                    else:
                        impact = "risk"
                        severity = "low"
                        summary = f"⚖️ MARKET STABLE: ASPI consolidating near 5-day average (LKR {current_price:.2f})."

                    insights_list.append({
                        "source_event_id": str(uuid.uuid4()),
                        "domain": "economical",
                        "severity": severity,
                        "impact_type": impact,
                        "summary": summary,
                        "risk_score": 0.3 if impact == "opportunity" else 0.5
                    })
            except Exception as e:
                print(f"[ECONOMIC] Math analysis failed: {e}")

        # News Analysis
        for news in news_items:
            headline = news.get('headline', '')
            is_good_news = any(x in headline.lower() for x in ['growth', 'profit', 'up', 'approved', 'gain'])
            
            insights_list.append({
                "source_event_id": str(uuid.uuid4()),
                "domain": "economical",
                "severity": "medium",
                "impact_type": "opportunity" if is_good_news else "risk",
                "summary": f"📰 {headline}",
                "risk_score": 0.4
            })

        print(f"  ✓ Generated {len(insights_list)} insights")
        
        # CRITICAL: Return domain_insights for Mother Graph
        return {
            "domain_insights": insights_list,
            "final_feed": json.dumps(insights_list, indent=2)
        }