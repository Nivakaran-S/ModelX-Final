"""
main.py
Main entry point for ModelX Platform
Run this to test the complete system
"""
import json
from datetime import datetime
from src.graphs.ModelXGraph import graph
from src.states.combinedAgentState import CombinedAgentState


def run_modelx_platform():
    """
    Executes the complete ModelX platform and displays results.
    """
    print("\n" + "=" * 80)
    print("🇱🇰 MODELX - SRI LANKA NATIONAL SITUATIONAL AWARENESS PLATFORM")
    print("=" * 80)
    print(f"Execution Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    # Initialize state
    initial_state = CombinedAgentState()
    
    print("\n[SYSTEM] Initializing ModelX platform...")
    print("[SYSTEM] Starting Fan-Out/Fan-In execution...")
    print()
    
    try:
        # Execute the graph
        result = graph.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✓ EXECUTION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        # Display Results
        display_results(result)
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def display_results(result):
    """
    Formats and displays ModelX results.
    """
    
    # 1. Risk Dashboard
    print("\n" + "=" * 80)
    print("📊 OPERATIONAL RISK RADAR")
    print("=" * 80)
    
    snapshot = result.get("risk_dashboard_snapshot", {})
    
    print(f"""
╔══════════════════════════════════════╗
║  LOGISTICS FRICTION:      {snapshot.get('logistics_friction', 0.0):.3f}    ║
║  COMPLIANCE VOLATILITY:   {snapshot.get('compliance_volatility', 0.0):.3f}    ║
║  MARKET INSTABILITY:      {snapshot.get('market_instability', 0.0):.3f}    ║
╠══════════════════════════════════════╣
║  AVG CONFIDENCE:          {snapshot.get('avg_confidence', 0.0):.3f}    ║
║  HIGH PRIORITY EVENTS:    {snapshot.get('high_priority_count', 0)}        ║
║  TOTAL EVENTS:            {snapshot.get('total_events', 0)}        ║
╚══════════════════════════════════════╝
""")
    
    # 2. National Activity Feed
    print("=" * 80)
    print("📰 NATIONAL ACTIVITY FEED")
    print("=" * 80)
    
    feed = result.get("final_ranked_feed", [])
    
    if not feed:
        print("\n⚠️  No events detected in current scan")
    else:
        print(f"\nShowing top {min(10, len(feed))} events (sorted by priority):\n")
        
        for i, event in enumerate(feed[:10], 1):
            domain = event.get("target_agent", "unknown").upper()
            confidence = event.get("confidence_score", 0.0)
            severity = event.get("severity", "unknown").upper()
            summary = event.get("content_summary", "No summary")[:200]
            
            print(f"{i}. [{domain}] Confidence: {confidence:.3f} | Severity: {severity}")
            print(f"   {summary}...")
            print()
    
    # 3. Execution Metadata
    print("=" * 80)
    print("🔄 EXECUTION METADATA")
    print("=" * 80)
    
    run_count = result.get("run_count", 0)
    last_run = result.get("last_run_ts")
    
    print(f"""
Total Iterations:     {run_count}
Last Execution:       {last_run}
Routing Decision:     {'LOOP' if result.get('route') == 'GraphInitiator' else 'END'}
""")
    
    # 4. Export Results
    print("=" * 80)
    print("💾 EXPORTING RESULTS")
    print("=" * 80)
    
    export_results_to_json(result)


def export_results_to_json(result):
    """
    Exports results to JSON file for further analysis.
    """
    try:
        # Convert datetime objects to strings
        export_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "risk_dashboard": result.get("risk_dashboard_snapshot", {}),
            "events": result.get("final_ranked_feed", []),
            "metadata": {
                "run_count": result.get("run_count", 0),
                "last_run": str(result.get("last_run_ts", ""))
            }
        }
        
        filename = f"modelx_output_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✓ Results exported to: {filename}")
        
    except Exception as e:
        print(f"✗ Export failed: {e}")


def run_single_agent_test(agent_name: str):
    """
    Test individual domain agents.
    
    Args:
        agent_name: One of ['social', 'political', 'economical', 
                           'meteorological', 'intelligence', 'data_retrieval']
    """
    print(f"\n[TEST] Running {agent_name.upper()} Agent Test\n")
    
    if agent_name == "social":
        from src.graphs.socialAgentGraph import graph as agent_graph
        from src.states.socialAgentState import SocialAgentState
        state = SocialAgentState()
    elif agent_name == "political":
        from src.graphs.politicalAgentGraph import graph as agent_graph
        from src.states.politicalAgentState import PoliticalAgentState
        state = PoliticalAgentState()
    elif agent_name == "economical":
        from src.graphs.economicalAgentGraph import graph as agent_graph
        from src.states.economicalAgentState import EconomicalAgentState
        state = EconomicalAgentState()
    elif agent_name == "meteorological":
        from src.graphs.meteorologicalAgentGraph import graph as agent_graph
        from src.states.meteorologicalAgentState import MeteorologicalAgentState
        state = MeteorologicalAgentState()
    elif agent_name == "intelligence":
        from src.graphs.intelligenceAgentGraph import graph as agent_graph
        from src.states.intelligenceAgentState import IntelligenceAgentState
        state = IntelligenceAgentState()
    elif agent_name == "data_retrieval":
        from src.graphs.dataRetrievalAgentGraph import graph as agent_graph
        from src.states.dataRetrievalAgentState import DataRetrievalAgentState
        state = DataRetrievalAgentState()
    else:
        print(f"Unknown agent: {agent_name}")
        return
    
    try:
        result = agent_graph.invoke(state)
        
        print(f"\n✓ {agent_name.upper()} Agent Test Completed")
        print("\nOutput:")
        print(f"  Domain Insights: {len(result.get('domain_insights', []))} items")
        
        if 'final_feed' in result:
            print(f"\n{result['final_feed']}")
        
        return result
        
    except Exception as e:
        print(f"\n✗ Test Failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test individual agent
        agent_name = sys.argv[1].lower()
        run_single_agent_test(agent_name)
    else:
        # Run full system
        run_modelx_platform()