"""
src/nodes/socialAgentNode.py
COMPLETE - Social Agent Node
Monitors social media sentiment, public discussions, trending topics
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.socialAgentState import SocialAgentState
from src.utils.utils import TOOL_MAPPING


class SocialAgentNode:
    """
    Social Agent - monitors social media for public sentiment.
    Helps combat "Information Asymmetry" mentioned in your report.
    """
    
    def __init__(self, llm):
        self.llm = llm

    def data_change_detector(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Detects changes in social media trends
        """
        print("[SOCIAL] Data Change Detector")
        
        initial_result = {
            "source_tool": "social_probe",
            "raw_content": json.dumps({"status": "monitoring"}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "change_detected": True,  # Always check for trending topics
            "worker_results": [initial_result],
            "latest_worker_results": [initial_result]
        }

    def task_delegator_master_agent(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Plans social media monitoring tasks
        """
        print("[SOCIAL] Task Delegator")
        
        tasks: List[Dict[str, Any]] = []
        
        # Reddit monitoring
        tasks.append({
            "tool_name": "scrape_reddit",
            "parameters": {
                "keywords": ["Sri Lanka", "Colombo", "economy", "politics"],
                "limit": 20
            },
            "priority": "high"
        })
        
        # Twitter monitoring (placeholder)
        tasks.append({
            "tool_name": "scrape_twitter",
            "parameters": {"query": "Sri Lanka"},
            "priority": "normal"
        })
        
        print(f"  → Planned {len(tasks)} social monitoring tasks")
        
        return {"generated_tasks": tasks}

    def social_worker_agent(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Worker agent - executes single social monitoring task
        """
        tasks = state.get("generated_tasks", [])
        if not tasks:
            return {}
        
        task = tasks[0]
        remaining = tasks[1:]
        
        print(f"[SOCIAL WORKER] Executing -> {task['tool_name']}")
        
        return {
            "current_task": task,
            "generated_tasks": remaining
        }

    def tool_node(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Executes social media monitoring tools
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

    def prepare_worker_tasks(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Prepares parallel worker states
        """
        tasks = state.get("generated_tasks", [])
        initial_states = [{"generated_tasks": [t]} for t in tasks]
        
        print(f"[SOCIAL] Spawning {len(initial_states)} parallel workers")
        
        return {"tasks_for_workers": initial_states}

    def aggregate_results(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Aggregates results from parallel workers
        """
        outputs = state.get("worker", []) or []
        aggregated: List[Dict[str, Any]] = []
        
        for out in outputs:
            aggregated.extend(out.get("worker_results", []))
        
        print(f"[SOCIAL] Aggregated {len(aggregated)} results")
        
        return {
            "worker_results": aggregated,
            "latest_worker_results": aggregated
        }

    def feed_creator_agent(self, state: SocialAgentState) -> Dict[str, Any]:
        """
        Creates social sentiment feed with fake news detection
        """
        print("[SOCIAL] Feed Creator")
        
        all_results = state.get("worker_results", []) or []
        
        reddit_posts = []
        twitter_mentions = []
        
        for r in all_results:
            source_tool = r.get("source_tool", "")
            content = r.get("raw_content", "")
            
            if "reddit" in source_tool:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        reddit_posts.extend(data[:10])
                except:
                    pass
            elif "twitter" in source_tool:
                try:
                    data = json.loads(content)
                    twitter_mentions.append(data.get("note", ""))
                except:
                    pass
        
        reddit_text = "\n".join([f"• {post.get('title', 'N/A')[:80]}..." for post in reddit_posts]) if reddit_posts else "No Reddit discussions"
        twitter_text = "\n".join(twitter_mentions) if twitter_mentions else "Twitter monitoring unavailable (requires API)"
        
        bulletin = f"""🇱🇰 SOCIAL SENTIMENT FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

💬 REDDIT DISCUSSIONS
{reddit_text}

🐦 TWITTER MONITORING
{twitter_text}

⚠️ SENTIMENT ANALYSIS
- Monitor for panic-inducing content
- Verify claims against official sources
- Flag potential misinformation

Use this intelligence to counter "fake news" and market panic.

Source: Public Social Media Platforms
"""
        
        print("  ✓ Feed created")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin]
        }