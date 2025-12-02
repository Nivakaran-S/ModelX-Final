"""
src/nodes/politicalAgentNode.py
MODULAR - Political Agent Node with Subgraph Architecture
Three modules: Official Sources, Social Media Collection, Feed Generation
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime
from src.states.politicalAgentState import PoliticalAgentState
from src.utils.utils import TOOL_MAPPING
from src.llms.groqllm import GroqLLM


class PoliticalAgentNode:
    """
    Modular Political Agent - Three independent collection modules.
    Module 1: Official Sources (Gazette, Parliament)
    Module 2: Social Media (National, District, World)
    Module 3: Feed Generation (Categorize, Summarize, Format)
    """
    
    def __init__(self, llm=None):
        """Initialize with Groq LLM"""
        if llm is None:
            groq = GroqLLM()
            self.llm = groq.get_llm()
        else:
            self.llm = llm
        
        # All 25 districts of Sri Lanka
        self.districts = [
            "colombo", "gampaha", "kalutara", "kandy", "matale", 
            "nuwara eliya", "galle", "matara", "hambantota", 
            "jaffna", "kilinochchi", "mannar", "mullaitivu", "vavuniya",
            "puttalam", "kurunegala", "anuradhapura", "polonnaruwa",
            "badulla", "monaragala", "ratnapura", "kegalle",
            "ampara", "batticaloa", "trincomalee"
        ]
        
        # Key districts to monitor per run (to avoid overwhelming)
        self.key_districts = ["colombo", "kandy", "jaffna", "galle", "kurunegala"]

    # ============================================
    # MODULE 1: OFFICIAL SOURCES COLLECTION
    # ============================================
    
    def collect_official_sources(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 1: Collect official government sources in parallel
        - Government Gazette
        - Parliament Minutes
        """
        print("[MODULE 1] Collecting Official Sources")
        
        official_results = []
        
        # Government Gazette
        try:
            gazette_tool = TOOL_MAPPING.get("scrape_government_gazette")
            if gazette_tool:
                gazette_data = gazette_tool.invoke({
                    "keywords": ["sri lanka tax", "sri lanka regulation", "sri lanka policy"],
                    "max_items": 15
                })
                official_results.append({
                    "source_tool": "scrape_government_gazette",
                    "raw_content": str(gazette_data),
                    "category": "official",
                    "subcategory": "gazette",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Scraped Government Gazette")
        except Exception as e:
            print(f"  ⚠️ Gazette error: {e}")
        
        # Parliament Minutes
        try:
            parliament_tool = TOOL_MAPPING.get("scrape_parliament_minutes")
            if parliament_tool:
                parliament_data = parliament_tool.invoke({
                    "keywords": ["sri lanka bill", "sri lanka amendment", "sri lanka budget"],
                    "max_items": 20
                })
                official_results.append({
                    "source_tool": "scrape_parliament_minutes",
                    "raw_content": str(parliament_data),
                    "category": "official",
                    "subcategory": "parliament",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Scraped Parliament Minutes")
        except Exception as e:
            print(f"  ⚠️ Parliament error: {e}")
        
        return {
            "worker_results": official_results,
            "latest_worker_results": official_results
        }

    # ============================================
    # MODULE 2: SOCIAL MEDIA COLLECTION
    # ============================================
    
    def collect_national_social_media(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 2A: Collect national-level social media
        """
        print("[MODULE 2A] Collecting National Social Media")
        
        social_results = []
        
        # Twitter - National
        try:
            twitter_tool = TOOL_MAPPING.get("scrape_twitter")
            if twitter_tool:
                twitter_data = twitter_tool.invoke({
                    "query": "sri lanka politics government",
                    "max_items": 15
                })
                social_results.append({
                    "source_tool": "scrape_twitter",
                    "raw_content": str(twitter_data),
                    "category": "national",
                    "platform": "twitter",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Twitter National")
        except Exception as e:
            print(f"  ⚠️ Twitter error: {e}")
        
        # Facebook - National
        try:
            facebook_tool = TOOL_MAPPING.get("scrape_facebook")
            if facebook_tool:
                facebook_data = facebook_tool.invoke({
                    "keywords": ["sri lanka politics", "sri lanka government"],
                    "max_items": 10
                })
                social_results.append({
                    "source_tool": "scrape_facebook",
                    "raw_content": str(facebook_data),
                    "category": "national",
                    "platform": "facebook",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Facebook National")
        except Exception as e:
            print(f"  ⚠️ Facebook error: {e}")
        
        # LinkedIn - National
        try:
            linkedin_tool = TOOL_MAPPING.get("scrape_linkedin")
            if linkedin_tool:
                linkedin_data = linkedin_tool.invoke({
                    "keywords": ["sri lanka policy", "sri lanka government"],
                    "max_items": 5
                })
                social_results.append({
                    "source_tool": "scrape_linkedin",
                    "raw_content": str(linkedin_data),
                    "category": "national",
                    "platform": "linkedin",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ LinkedIn National")
        except Exception as e:
            print(f"  ⚠️ LinkedIn error: {e}")
        
        # Instagram - National
        try:
            instagram_tool = TOOL_MAPPING.get("scrape_instagram")
            if instagram_tool:
                instagram_data = instagram_tool.invoke({
                    "keywords": ["srilankapolitics"],
                    "max_items": 5
                })
                social_results.append({
                    "source_tool": "scrape_instagram",
                    "raw_content": str(instagram_data),
                    "category": "national",
                    "platform": "instagram",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Instagram National")
        except Exception as e:
            print(f"  ⚠️ Instagram error: {e}")
        
        # Reddit - National
        try:
            reddit_tool = TOOL_MAPPING.get("scrape_reddit")
            if reddit_tool:
                reddit_data = reddit_tool.invoke({
                    "keywords": ["sri lanka politics"],
                    "limit": 10,
                    "subreddit": "srilanka"
                })
                social_results.append({
                    "source_tool": "scrape_reddit",
                    "raw_content": str(reddit_data),
                    "category": "national",
                    "platform": "reddit",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Reddit National")
        except Exception as e:
            print(f"  ⚠️ Reddit error: {e}")
        
        return {
            "worker_results": social_results,
            "social_media_results": social_results
        }
    
    def collect_district_social_media(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 2B: Collect district-level social media for key districts
        """
        print(f"[MODULE 2B] Collecting District Social Media ({len(self.key_districts)} districts)")
        
        district_results = []
        
        for district in self.key_districts:
            # Twitter per district
            try:
                twitter_tool = TOOL_MAPPING.get("scrape_twitter")
                if twitter_tool:
                    twitter_data = twitter_tool.invoke({
                        "query": f"{district} sri lanka",
                        "max_items": 5
                    })
                    district_results.append({
                        "source_tool": "scrape_twitter",
                        "raw_content": str(twitter_data),
                        "category": "district",
                        "district": district,
                        "platform": "twitter",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    print(f"  ✓ Twitter {district.title()}")
            except Exception as e:
                print(f"  ⚠️ Twitter {district} error: {e}")
            
            # Facebook per district
            try:
                facebook_tool = TOOL_MAPPING.get("scrape_facebook")
                if facebook_tool:
                    facebook_data = facebook_tool.invoke({
                        "keywords": [f"{district} sri lanka"],
                        "max_items": 5
                    })
                    district_results.append({
                        "source_tool": "scrape_facebook",
                        "raw_content": str(facebook_data),
                        "category": "district",
                        "district": district,
                        "platform": "facebook",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    print(f"  ✓ Facebook {district.title()}")
            except Exception as e:
                print(f"  ⚠️ Facebook {district} error: {e}")
        
        return {
            "worker_results": district_results,
            "social_media_results": district_results
        }
    
    def collect_world_politics(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 2C: Collect world politics affecting Sri Lanka
        """
        print("[MODULE 2C] Collecting World Politics")
        
        world_results = []
        
        # Twitter - World Politics
        try:
            twitter_tool = TOOL_MAPPING.get("scrape_twitter")
            if twitter_tool:
                twitter_data = twitter_tool.invoke({
                    "query": "sri lanka international relations IMF",
                    "max_items": 10
                })
                world_results.append({
                    "source_tool": "scrape_twitter",
                    "raw_content": str(twitter_data),
                    "category": "world",
                    "platform": "twitter",
                    "timestamp": datetime.utcnow().isoformat()
                })
                print("  ✓ Twitter World Politics")
        except Exception as e:
            print(f"  ⚠️ Twitter world error: {e}")
        
        return {
            "worker_results": world_results,
            "social_media_results": world_results
        }

    # ============================================
    # MODULE 3: FEED GENERATION
    # ============================================
    
    def categorize_by_geography(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 3A: Categorize all collected results by geography
        """
        print("[MODULE 3A] Categorizing Results by Geography")
        
        all_results = state.get("worker_results", []) or []
        
        # Initialize categories
        official_data = []
        national_data = []
        world_data = []
        district_data = {district: [] for district in self.districts}
        
        for r in all_results:
            category = r.get("category", "unknown")
            district = r.get("district")
            content = r.get("raw_content", "")
            
            # Parse content
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "error" in data:
                    continue
                
                if isinstance(data, str):
                    data = json.loads(data)
                
                posts = []
                if isinstance(data, list):
                    posts = data
                elif isinstance(data, dict):
                    posts = data.get("results", []) or data.get("data", [])
                    if not posts:
                        posts = [data]
                
                # Categorize
                if category == "official":
                    official_data.extend(posts[:10])
                elif category == "world":
                    world_data.extend(posts[:10])
                elif category == "district" and district:
                    district_data[district].extend(posts[:5])
                elif category == "national":
                    national_data.extend(posts[:10])
                    
            except Exception as e:
                continue
        
        # Create structured feeds
        structured_feeds = {
            "sri lanka": national_data + official_data,
            "world": world_data,
            **{district: posts for district, posts in district_data.items() if posts}
        }
        
        print(f"  ✓ Categorized: {len(official_data)} official, {len(national_data)} national, {len(world_data)} world")
        print(f"  ✓ Districts with data: {len([d for d in district_data if district_data[d]])}")
        
        return {
            "structured_output": structured_feeds,
            "district_feeds": district_data,
            "national_feed": national_data + official_data,
            "world_feed": world_data
        }
    
    def generate_llm_summary(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 3B: Use Groq LLM to generate executive summary
        """
        print("[MODULE 3B] Generating LLM Summary")
        
        structured_feeds = state.get("structured_output", {})
        
        try:
            summary_prompt = f"""Analyze the following political intelligence data for Sri Lanka and create a concise executive summary.

Data Summary:
- National/Official: {len(structured_feeds.get('sri lanka', []))} items
- World Politics: {len(structured_feeds.get('world', []))} items
- District Coverage: {len([k for k in structured_feeds.keys() if k not in ['sri lanka', 'world']])} districts

Sample Data:
{json.dumps(structured_feeds, indent=2)[:2000]}

Generate a brief (3-5 sentences) executive summary highlighting the most important political developments."""

            llm_response = self.llm.invoke(summary_prompt)
            llm_summary = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            print("  ✓ LLM Summary Generated")
            
        except Exception as e:
            print(f"  ⚠️ LLM Error: {e}")
            llm_summary = "AI summary currently unavailable."
        
        return {
            "llm_summary": llm_summary
        }
    
    def format_final_output(self, state: PoliticalAgentState) -> Dict[str, Any]:
        """
        Module 3C: Format final feed output
        """
        print("[MODULE 3C] Formatting Final Output")
        
        llm_summary = state.get("llm_summary", "No summary available")
        structured_feeds = state.get("structured_output", {})
        district_feeds = state.get("district_feeds", {})
        
        official_count = len([r for r in state.get("worker_results", []) if r.get("category") == "official"])
        national_count = len([r for r in state.get("worker_results", []) if r.get("category") == "national"])
        world_count = len([r for r in state.get("worker_results", []) if r.get("category") == "world"])
        active_districts = len([d for d in district_feeds if district_feeds.get(d)])
        
        bulletin = f"""🇱🇰 COMPREHENSIVE POLITICAL INTELLIGENCE FEED
{datetime.utcnow().strftime("%d %b %Y • %H:%M UTC")}

📊 EXECUTIVE SUMMARY (AI-Generated)
{llm_summary}

📈 DATA COLLECTION STATS
• Official Sources: {official_count} items
• National Social Media: {national_count} items
• World Politics: {world_count} items  
• Active Districts: {active_districts}

🔍 COVERAGE
Districts monitored: {', '.join([d.title() for d in self.key_districts])}

🌐 STRUCTURED DATA AVAILABLE
• "sri lanka": Combined national & official intelligence
• "world": International relations & global impact
• District-level: {', '.join([d.title() for d in district_feeds if district_feeds.get(d)])}

Source: Multi-platform aggregation (Twitter, Facebook, LinkedIn, Instagram, Reddit, Government Gazette, Parliament)
"""
        
        # Create integration output
        insight = {
            "source_event_id": str(uuid.uuid4()),
            "domain": "political",
            "severity": "high",
            "summary": llm_summary,
            "risk_score": 0.7,
            "structured_data": structured_feeds
        }
        
        print("  ✓ Final Feed Formatted")
        
        return {
            "final_feed": bulletin,
            "feed_history": [bulletin],
            "domain_insights": [insight]
        }