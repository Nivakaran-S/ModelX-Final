"""
backend/api/main.py
FastAPI server to expose ModelX graph state to frontend
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import asyncio
import json
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graphs.ModelXGraph import graph
from src.states.combinedAgentState import CombinedAgentState

app = FastAPI(title="ModelX Intelligence Platform API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state storage
current_state: Dict[str, Any] = {
    "final_ranked_feed": [],
    "risk_dashboard_snapshot": {
        "logistics_friction": 0.0,
        "compliance_volatility": 0.0,
        "market_instability": 0.0,
        "opportunity_index": 0.0,
        "avg_confidence": 0.0,
        "high_priority_count": 0,
        "total_events": 0,
        "last_updated": datetime.utcnow().isoformat()
    },
    "run_count": 0,
    "status": "initializing"
}

active_connections: List[WebSocket] = []

# Background task to run the graph
async def run_graph_loop():
    """Continuously runs the ModelX graph and updates state"""
    global current_state
    
    print("[API] Starting ModelX graph loop...")
    
    # Initial state
    initial_state = CombinedAgentState(
        domain_insights=[],
        final_ranked_feed=[],
        run_count=0,
        max_runs=999,  # Continuous mode
        route=None
    )
    
    try:
        # Stream graph execution
        async for event in graph.astream(initial_state):
            # Extract state updates
            for node_name, node_output in event.items():
                print(f"[API] Node: {node_name}")
                
                # Update global state with latest outputs
                if hasattr(node_output, 'final_ranked_feed'):
                    current_state['final_ranked_feed'] = [
                        {
                            "event_id": e.get("event_id"),
                            "domain": e.get("target_agent"),
                            "severity": e.get("severity"),
                            "impact_type": e.get("impact_type", "risk"),
                            "summary": e.get("content_summary"),
                            "confidence": e.get("confidence_score"),
                            "timestamp": e.get("timestamp")
                        }
                        for e in node_output.final_ranked_feed
                    ]
                
                if hasattr(node_output, 'risk_dashboard_snapshot'):
                    current_state['risk_dashboard_snapshot'] = node_output.risk_dashboard_snapshot
                
                if hasattr(node_output, 'run_count'):
                    current_state['run_count'] = node_output.run_count
                
                current_state['status'] = 'operational'
                current_state['last_update'] = datetime.utcnow().isoformat()
                
                # Broadcast to all connected WebSocket clients
                await broadcast_state()
                
                # Small delay for UI responsiveness
                await asyncio.sleep(0.5)
                
    except Exception as e:
        print(f"[API] Graph error: {e}")
        current_state['status'] = 'error'
        current_state['error'] = str(e)

async def broadcast_state():
    """Send current state to all WebSocket clients"""
    if not active_connections:
        return
    
    message = json.dumps(current_state, default=str)
    
    # Remove disconnected clients
    dead_connections = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            dead_connections.append(connection)
    
    for conn in dead_connections:
        active_connections.remove(conn)

@app.on_event("startup")
async def startup_event():
    """Start the graph loop when API starts"""
    asyncio.create_task(run_graph_loop())

@app.get("/")
def read_root():
    return {
        "service": "ModelX Intelligence Platform",
        "status": current_state.get("status"),
        "version": "1.0.0"
    }

@app.get("/api/status")
def get_status():
    """Get current system status"""
    return {
        "status": current_state.get("status"),
        "run_count": current_state.get("run_count"),
        "last_update": current_state.get("last_update"),
        "active_connections": len(active_connections)
    }

@app.get("/api/dashboard")
def get_dashboard():
    """Get risk dashboard snapshot"""
    return current_state.get("risk_dashboard_snapshot", {})

@app.get("/api/feed")
def get_feed():
    """Get latest ranked intelligence feed"""
    return {
        "events": current_state.get("final_ranked_feed", []),
        "total": len(current_state.get("final_ranked_feed", []))
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send initial state
    await websocket.send_text(json.dumps(current_state, default=str))
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)