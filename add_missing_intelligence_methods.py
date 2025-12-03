"""
add_missing_intelligence_methods.py
Adds the 3 missing competitive intelligence collection methods
"""

MISSING_METHODS = '''
    # ============================================
    # MODULE 2: COMPETITIVE INTELLIGENCE COLLECTION
    # ============================================
    
    def collect_competitor_mentions(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Collect competitor mentions from social media
        """
        print("[MODULE 2A] Competitor Mentions")
        
        competitor_results = []
        
        # Twitter competitor tracking
        try:
            twitter_tool = TOOL_MAPPING.get("scrape_twitter")
            if twitter_tool:
                for competitor in self.local_competitors[:3]:
                    try:
                        data = twitter_tool.invoke({
                            "query": competitor,
                            "max_items": 10
                        })
                        competitor_results.append({
                            "source_tool": "scrape_twitter",
                            "raw_content": str(data),
                            "category": "competitor_mention",
                            "subcategory": "twitter",
                            "entity": competitor,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        print(f"  [OK] Tracked {competitor} on Twitter")
                    except Exception as e:
                        print(f"  [WARN] {competitor} error: {e}")
        except Exception as e:
            print(f"  [WARN] Twitter tracking error: {e}")
        
        # Reddit competitor discussions
        try:
            reddit_tool = TOOL_MAPPING.get("scrape_reddit")
            if reddit_tool:
                for competitor in self.local_competitors[:2]:
                    try:
                        data = reddit_tool.invoke({
                            "keywords": [competitor, f"{competitor} sri lanka"],
                            "limit": 10
                        })
                        competitor_results.append({
                            "source_tool": "scrape_reddit",
                            "raw_content": str(data),
                            "category": "competitor_mention",
                            "subcategory": "reddit",
                            "entity": competitor,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        print(f"  [OK] Tracked {competitor} on Reddit")
                    except Exception as e:
                        print(f"  [WARN] Reddit {competitor} error: {e}")
        except Exception as e:
            print(f"  [WARN] Reddit tracking error: {e}")
        
        return {
            "worker_results": competitor_results,
            "latest_worker_results": competitor_results
        }
    
    def collect_product_reviews(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Collect product reviews and sentiment
        """
        print("[MODULE 2B] Product Reviews")
        
        review_results = []
        
        try:
            review_tool = TOOL_MAPPING.get("scrape_product_reviews")
            if review_tool:
                for product in self.product_watchlist:
                    try:
                        data = review_tool.invoke({
                            "product_keyword": product,
                            "platforms": ["reddit", "twitter"],
                            "max_items": 10
                        })
                        review_results.append({
                            "source_tool": "scrape_product_reviews",
                            "raw_content": str(data),
                            "category": "product_review",
                            "subcategory": "multi_platform",
                            "product": product,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        print(f"  [OK] Collected reviews for {product}")
                    except Exception as e:
                        print(f"  [WARN] {product} error: {e}")
        except Exception as e:
            print(f"  [WARN] Product review error: {e}")
        
        return {
            "worker_results": review_results,
            "latest_worker_results": review_results
        }
    
    def collect_market_intelligence(self, state: IntelligenceAgentState) -> Dict[str, Any]:
        """
        Collect broader market intelligence
        """
        print("[MODULE 2C] Market Intelligence")
        
        market_results = []
        
        # Industry news and trends
        try:
            twitter_tool = TOOL_MAPPING.get("scrape_twitter")
            if twitter_tool:
                for keyword in ["telecom sri lanka", "5G sri lanka", "fiber broadband"]:
                    try:
                        data = twitter_tool.invoke({
                            "query": keyword,
                            "max_items": 10
                        })
                        market_results.append({
                            "source_tool": "scrape_twitter",
                            "raw_content": str(data),
                            "category": "market_intelligence",
                            "subcategory": "industry_trends",
                            "keyword": keyword,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        print(f"  [OK] Tracked '{keyword}'")
                    except Exception as e:
                        print(f"  [WARN] '{keyword}' error: {e}")
        except Exception as e:
            print(f"  [WARN] Market intelligence error: {e}")
        
        return {
            "worker_results": market_results,
            "latest_worker_results": market_results
        }
'''

def main():
    print("=" * 60)
    print("Adding Missing Intelligence Collection Methods")
    print("=" * 60)
    
    print("\n1. Reading intelligenceAgentNode.py...")
    with open('src/nodes/intelligenceAgentNode.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if methods already exist
    if 'def collect_competitor_mentions' in content:
        print("   [OK] Methods already present!")
        return True
    
    # Find insertion point (after collect_profile_activity method)
    print("\n2. Finding insertion point...")
    marker = "    # ============================================\n    # MODULE 3: FEED GENERATION\n    # ============================================"
    
    if marker in content:
        # Insert before Module 3
        content = content.replace(marker, MISSING_METHODS + "\n" + marker)
        print("   [OK] Found insertion point")
    else:
        print("   [ERROR] Could not find insertion point")
        return False
    
    # Write back
    print("\n3. Writing updated file...")
    with open('src/nodes/intelligenceAgentNode.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Verify
    print("\n4. Verifying syntax...")
    import py_compile
    try:
        py_compile.compile('src/nodes/intelligenceAgentNode.py', doraise=True)
        print("   [OK] File is valid Python")
    except SyntaxError as e:
        print(f"   [ERROR] Syntax error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("SUCCESS! Added 3 missing methods:")
    print("  - collect_competitor_mentions")
    print("  - collect_product_reviews")
    print("  - collect_market_intelligence")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
