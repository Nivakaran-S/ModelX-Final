"""
app.py
Streamlit Dashboard for ModelX Platform
Interactive interface to test and visualize the ModelX graph
"""
import streamlit as st
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Import ModelX components
from src.graphs.ModelXGraph import graph
from src.states.combinedAgentState import CombinedAgentState

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="ModelX - Situational Awareness Platform",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .event-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .severity-high {
        color: #ff4444;
        font-weight: bold;
    }
    .severity-medium {
        color: #ff9800;
        font-weight: bold;
    }
    .severity-low {
        color: #4caf50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER
# ============================================

st.markdown('<div class="main-header">🇱🇰 ModelX</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">National Situational Awareness Platform</div>', unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Execution Settings")
    max_iterations = st.slider("Max Iterations", 1, 10, 5)
    
    st.subheader("Monitoring Focus")
    monitor_political = st.checkbox("Political Intelligence", value=True)
    monitor_economic = st.checkbox("Economic Data", value=True)
    monitor_weather = st.checkbox("Weather Alerts", value=True)
    monitor_social = st.checkbox("Social Media", value=True)
    monitor_intelligence = st.checkbox("Brand Intelligence", value=True)
    
    st.divider()
    
    st.subheader("About ModelX")
    st.info("""
    **Team Adagard**  
    Open Innovation Track
    
    ModelX transforms national-scale noise into actionable business intelligence using autonomous multi-agent architecture.
    """)
    
    st.subheader("Architecture")
    st.code("""
START → GraphInitiator
  ↓ (Fan-Out)
6 Domain Agents (Parallel)
  ↓ (Fan-In)
FeedAggregator → Dashboard
  ↓
Router (Loop/End)
    """, language="text")

# ============================================
# MAIN CONTENT
# ============================================

# Initialize session state
if "execution_history" not in st.session_state:
    st.session_state.execution_history = []

if "current_result" not in st.session_state:
    st.session_state.current_result = None

# ============================================
# EXECUTION CONTROL
# ============================================

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🚀 Run ModelX Analysis", type="primary", use_container_width=True):
        with st.spinner("🔄 Executing ModelX platform..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Update progress
                status_text.text("Initializing agents...")
                progress_bar.progress(20)
                time.sleep(0.5)
                
                # Create initial state
                initial_state = CombinedAgentState(max_runs=max_iterations)
                
                status_text.text("Running Fan-Out/Fan-In execution...")
                progress_bar.progress(40)
                
                # Execute graph
                result = graph.invoke(initial_state)
                
                status_text.text("Processing results...")
                progress_bar.progress(80)
                time.sleep(0.3)
                
                # Store result
                st.session_state.current_result = result
                st.session_state.execution_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": result
                })
                
                progress_bar.progress(100)
                status_text.text("✅ Execution completed!")
                time.sleep(0.5)
                status_text.empty()
                progress_bar.empty()
                
                st.success("Analysis completed successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Execution failed: {str(e)}")
                st.exception(e)

with col2:
    if st.button("📊 View JSON Export", use_container_width=True):
        if st.session_state.current_result:
            st.session_state.show_json = True
        else:
            st.warning("No results available. Run analysis first.")

with col3:
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.execution_history = []
        st.session_state.current_result = None
        st.rerun()

# ============================================
# RESULTS DISPLAY
# ============================================

if st.session_state.current_result:
    result = st.session_state.current_result
    
    st.divider()
    
    # ========== RISK DASHBOARD ==========
    st.header("📊 Operational Risk Radar")
    
    snapshot = result.get("risk_dashboard_snapshot", {})
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        logistics = snapshot.get("logistics_friction", 0.0)
        st.metric(
            "Logistics Friction",
            f"{logistics:.3f}",
            delta=None,
            help="Route risk score from mobility data"
        )
    
    with col2:
        compliance = snapshot.get("compliance_volatility", 0.0)
        st.metric(
            "Compliance Volatility",
            f"{compliance:.3f}",
            delta=None,
            help="Regulatory risk from political data"
        )
    
    with col3:
        market = snapshot.get("market_instability", 0.0)
        st.metric(
            "Market Instability",
            f"{market:.3f}",
            delta=None,
            help="Market volatility from economic data"
        )
    
    with col4:
        high_priority = snapshot.get("high_priority_count", 0)
        total_events = snapshot.get("total_events", 0)
        st.metric(
            "High Priority Events",
            f"{high_priority}/{total_events}",
            delta=None,
            help="Events with confidence >= 0.7"
        )
    
    # Risk Visualization
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=["Logistics", "Compliance", "Market"],
        y=[logistics, compliance, market],
        marker_color=['#ff9800', '#f44336', '#2196f3'],
        text=[f"{logistics:.3f}", f"{compliance:.3f}", f"{market:.3f}"],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Risk Metrics Overview",
        yaxis_title="Risk Score",
        xaxis_title="Domain",
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ========== NATIONAL ACTIVITY FEED ==========
    st.header("📰 National Activity Feed")
    
    feed = result.get("final_ranked_feed", [])
    
    if not feed:
        st.info("No events detected in current scan.")
    else:
        # Feed statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Events", len(feed))
        
        with col2:
            domains = [e.get("target_agent", "unknown") for e in feed]
            unique_domains = len(set(domains))
            st.metric("Active Domains", unique_domains)
        
        with col3:
            avg_conf = sum(e.get("confidence_score", 0) for e in feed) / len(feed)
            st.metric("Avg Confidence", f"{avg_conf:.3f}")
        
        # Domain distribution chart
        domain_counts = {}
        for event in feed:
            domain = event.get("target_agent", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        fig_domains = go.Figure(data=[go.Pie(
            labels=list(domain_counts.keys()),
            values=list(domain_counts.values()),
            hole=0.3
        )])
        
        fig_domains.update_layout(
            title="Events by Domain",
            height=300
        )
        
        st.plotly_chart(fig_domains, use_container_width=True)
        
        # Filter options
        st.subheader("Filter Events")
        col1, col2 = st.columns(2)
        
        with col1:
            severity_filter = st.multiselect(
                "Severity",
                ["critical", "high", "medium", "low"],
                default=["critical", "high", "medium", "low"]
            )
        
        with col2:
            domain_filter = st.multiselect(
                "Domain",
                list(set(domains)),
                default=list(set(domains))
            )
        
        # Display events
        st.subheader("Event Details")
        
        # Filter feed
        filtered_feed = [
            e for e in feed
            if e.get("severity", "medium") in severity_filter
            and e.get("target_agent", "unknown") in domain_filter
        ]
        
        if not filtered_feed:
            st.info("No events match the selected filters.")
        else:
            for i, event in enumerate(filtered_feed[:20], 1):  # Show top 20
                domain = event.get("target_agent", "unknown").upper()
                confidence = event.get("confidence_score", 0.0)
                severity = event.get("severity", "medium")
                summary = event.get("content_summary", "No summary")
                timestamp = event.get("timestamp", "")
                
                # Severity color
                severity_class = f"severity-{severity}"
                
                with st.expander(f"#{i} [{domain}] {summary[:80]}...", expanded=(i <= 3)):
                    st.markdown(f"""
                    **Domain:** {domain}  
                    **Confidence:** {confidence:.3f}  
                    **Severity:** <span class="{severity_class}">{severity.upper()}</span>  
                    **Timestamp:** {timestamp}
                    
                    ---
                    
                    **Summary:**  
                    {summary}
                    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== EXECUTION METADATA ==========
    st.header("🔄 Execution Metadata")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        run_count = result.get("run_count", 0)
        st.metric("Iterations", run_count)
    
    with col2:
        last_run = result.get("last_run_ts")
        if last_run:
            st.metric("Last Run", last_run.strftime("%H:%M:%S"))
        else:
            st.metric("Last Run", "N/A")
    
    with col3:
        route = result.get("route")
        routing_decision = "LOOP" if route == "GraphInitiator" else "END"
        st.metric("Routing Decision", routing_decision)
    
    # Timeline
    if len(st.session_state.execution_history) > 1:
        st.subheader("Execution History")
        
        history_data = []
        for h in st.session_state.execution_history[-10:]:  # Last 10
            ts = h["timestamp"]
            count = h["result"].get("run_count", 0)
            events = len(h["result"].get("final_ranked_feed", []))
            history_data.append({"Timestamp": ts, "Iterations": count, "Events": events})
        
        st.dataframe(history_data, use_container_width=True)

else:
    st.info("👆 Click 'Run ModelX Analysis' to start monitoring Sri Lanka's operational environment.")
    
    # Show sample architecture diagram
    st.subheader("How ModelX Works")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Fan-Out Phase
        1. **GraphInitiator** starts the cycle
        2. Dispatches to 6 domain agents:
           - Social Agent
           - Political Agent
           - Economic Agent
           - Meteorological Agent
           - Intelligence Agent
           - Data Retrieval Agent
        3. All agents execute **in parallel**
        """)
    
    with col2:
        st.markdown("""
        ### Fan-In Phase
        1. **FeedAggregator** collects insights
        2. Deduplicates and ranks by priority
        3. **DataRefresher** updates dashboard
        4. **Router** decides:
           - Loop if high confidence event
           - End if conditions met
        """)

# ============================================
# JSON EXPORT MODAL
# ============================================

if st.session_state.get("show_json", False) and st.session_state.current_result:
    with st.expander("📄 JSON Export", expanded=True):
        export_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "risk_dashboard": st.session_state.current_result.get("risk_dashboard_snapshot", {}),
            "events": st.session_state.current_result.get("final_ranked_feed", []),
            "metadata": {
                "run_count": st.session_state.current_result.get("run_count", 0),
                "last_run": str(st.session_state.current_result.get("last_run_ts", ""))
            }
        }
        
        st.json(export_data)
        
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(export_data, indent=2, default=str),
            file_name=f"modelx_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    st.session_state.show_json = False

# ============================================
# FOOTER
# ============================================

st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    ModelX Platform | Team Adagard | Open Innovation Track 2025<br>
    Built with LangGraph, Streamlit, and ❤️ for Sri Lanka
</div>
""", unsafe_allow_html=True)