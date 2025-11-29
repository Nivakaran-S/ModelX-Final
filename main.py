"""
backend/api/main.py
PRODUCTION - Resilient WebSocket handling with server heartbeat + robust broadcast
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import asyncio
import json
from datetime import datetime
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graphs.ModelXGraph import graph
from src.states.combinedAgentState import CombinedAgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("modelx_api")

app = FastAPI(title="ModelX Intelligence Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Heartbeat settings (tune as needed)
HEARTBEAT_INTERVAL = 25.0      # seconds between pings
HEARTBEAT_TIMEOUT = 10.0       # seconds to wait for a pong
HEARTBEAT_MISS_THRESHOLD = 3   # disconnect after this many missed pongs
SEND_TIMEOUT = 5.0             # timeout for socket send operations

class ConnectionManager:
    """
    Manages active WebSocket connections with per-connection heartbeat tasks and metadata.
    """
    def __init__(self):
        # Map WebSocket -> metadata dict
        # metadata: { "heartbeat_task": asyncio.Task, "last_pong": datetime, "misses": int }
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            # Initialize metadata
            meta = {
                "heartbeat_task": asyncio.create_task(self._heartbeat_loop(websocket)),
                "last_pong": datetime.utcnow(),
                "misses": 0
            }
            self.active_connections[websocket] = meta
            logger.info(f"✓ WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            meta = self.active_connections.pop(websocket, None)
        if meta:
            task = meta.get("heartbeat_task")
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            try:
                await websocket.close()
            except Exception:
                pass
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def _send_with_timeout(self, websocket: WebSocket, message_json: str):
        try:
            await asyncio.wait_for(websocket.send_text(message_json), timeout=SEND_TIMEOUT)
            return True
        except Exception as e:
            logger.debug(f"[SEND] send failed: {e}")
            return False

    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        Per-connection heartbeat task. Sends ping periodically and expects a 'pong' message
        from client within HEARTBEAT_TIMEOUT. Disconnects after HEARTBEAT_MISS_THRESHOLD misses.
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket not in self.active_connections:
                    break

                # Send ping
                ping_payload = json.dumps({"type": "ping"})
                ok = await self._send_with_timeout(websocket, ping_payload)
                if not ok:
                    # send failed — increment miss counter
                    async with self._lock:
                        meta = self.active_connections.get(websocket)
                        if meta is not None:
                            meta['misses'] += 1
                            logger.info(f"[HEARTBEAT] send failed, misses={meta['misses']}")
                else:
                    # sent; now wait up to HEARTBEAT_TIMEOUT for pong
                    waited = 0.0
                    sleep_step = 0.5
                    pong_received = False
                    while waited < HEARTBEAT_TIMEOUT:
                        await asyncio.sleep(sleep_step)
                        waited += sleep_step
                        async with self._lock:
                            meta = self.active_connections.get(websocket)
                            if meta is None:
                                # connection removed elsewhere
                                return
                            # If last_pong was updated recently, treat as pong
                            last_pong = meta.get("last_pong")
                            if last_pong and (datetime.utcnow() - last_pong).total_seconds() < (HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT):
                                pong_received = True
                                meta['misses'] = 0
                                break
                    if not pong_received:
                        async with self._lock:
                            meta = self.active_connections.get(websocket)
                            if meta is not None:
                                meta['misses'] += 1
                                logger.info(f"[HEARTBEAT] no pong received, misses={meta['misses']}")

                # If misses exceed threshold -> drop connection
                async with self._lock:
                    meta = self.active_connections.get(websocket)
                    if meta is None:
                        return
                    if meta.get('misses', 0) >= HEARTBEAT_MISS_THRESHOLD:
                        logger.warning("[HEARTBEAT] Miss threshold exceeded, disconnecting client")
                        # Best-effort close and cleanup
                        try:
                            await websocket.close(code=1001)
                        except Exception:
                            pass
                        # remove from active_connections
                        await self.disconnect(websocket)
                        return

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception(f"[HEARTBEAT] Unexpected error: {e}")
            # Ensure connection is cleaned up
            try:
                await self.disconnect(websocket)
            except Exception:
                pass

    async def broadcast(self, message: dict):
        """
        Broadcast a JSON message to all active connections. Clean up dead ones.
        """
        async with self._lock:
            conns = list(self.active_connections.keys())
        if not conns:
            return
        message_json = json.dumps(message, default=str)
        dead: List[WebSocket] = []
        for conn in conns:
            ok = await self._send_with_timeout(conn, message_json)
            if not ok:
                dead.append(conn)
        for conn in dead:
            logger.info("[BROADCAST] removing dead connection")
            await self.disconnect(conn)

manager = ConnectionManager()

def extract_state_data(node_output) -> Dict[str, Any]:
    """
    Extract data from node output regardless of format
    Handles: Pydantic models, dicts, objects with __dict__
    """
    data = {}
    
    # Try method 1: model_dump() for Pydantic v2
    if hasattr(node_output, 'model_dump'):
        try:
            data = node_output.model_dump()
            logger.debug(f"[EXTRACT] Used model_dump()")
            return data
        except:
            pass
    
    # Try method 2: dict() for Pydantic v1
    if hasattr(node_output, 'dict'):
        try:
            data = node_output.dict()
            logger.debug(f"[EXTRACT] Used dict()")
            return data
        except:
            pass
    
    # Try method 3: Direct dict conversion
    if isinstance(node_output, dict):
        logger.debug(f"[EXTRACT] Already a dict")
        return node_output
    
    # Try method 4: __dict__ attribute
    if hasattr(node_output, '__dict__'):
        logger.debug(f"[EXTRACT] Used __dict__")
        return node_output.__dict__
    
    # Try method 5: Direct attribute access
    result = {}
    for attr in ['final_ranked_feed', 'risk_dashboard_snapshot', 'run_count', 'domain_insights', 'route']:
        if hasattr(node_output, attr):
            result[attr] = getattr(node_output, attr)
    
    if result:
        logger.debug(f"[EXTRACT] Used direct attributes")
        return result
    
    logger.warning(f"[EXTRACT] Could not extract data from {type(node_output)}")
    return {}

async def run_graph_loop():
    """Run graph and extract state properly"""
    global current_state
    
    logger.info("=" * 80)
    logger.info("STARTING MODELX GRAPH LOOP")
    logger.info("=" * 80)
    
    initial_state = CombinedAgentState(
        domain_insights=[],
        final_ranked_feed=[],
        run_count=0,
        max_runs=999,
        route=None
    )
    
    try:
        async for event in graph.astream(initial_state):
            logger.info(f"[EVENT] Nodes: {list(event.keys())}")
            
            for node_name, node_output in event.items():
                logger.info(f"[NODE] Processing: {node_name}")
                
                # Extract state data using our helper
                state_data = extract_state_data(node_output)
                
                if not state_data:
                    logger.warning(f"[NODE] {node_name} - No data extracted")
                    continue
                
                logger.info(f"[NODE] {node_name} - Extracted keys: {list(state_data.keys())}")
                
                # Update current_state with extracted data
                updated = False
                
                # Extract feed
                if 'final_ranked_feed' in state_data and state_data['final_ranked_feed']:
                    feed = state_data['final_ranked_feed']
                    logger.info(f"[NODE] {node_name} - Found feed with {len(feed)} items")
                    
                    events = []
                    for e in feed:
                        # Handle both dict and object formats
                        if isinstance(e, dict):
                            event_data = e
                        else:
                            event_data = extract_state_data(e)
                        
                        events.append({
                            "event_id": event_data.get("event_id", "unknown"),
                            "domain": event_data.get("target_agent", event_data.get("domain", "unknown")),
                            "severity": event_data.get("severity", "medium"),
                            "impact_type": event_data.get("impact_type", "risk"),
                            "summary": event_data.get("content_summary", event_data.get("summary", "")),
                            "confidence": event_data.get("confidence_score", event_data.get("confidence", 0.5)),
                            "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat())
                        })
                    
                    current_state['final_ranked_feed'] = events
                    updated = True
                    logger.info(f"[UPDATE] Feed updated with {len(events)} events")
                
                # Extract dashboard
                if 'risk_dashboard_snapshot' in state_data and state_data['risk_dashboard_snapshot']:
                    dashboard = state_data['risk_dashboard_snapshot']
                    current_state['risk_dashboard_snapshot'] = dashboard
                    updated = True
                    logger.info(f"[UPDATE] Dashboard updated")
                
                # Extract run count
                if 'run_count' in state_data:
                    current_state['run_count'] = state_data['run_count']
                    updated = True
                    logger.info(f"[UPDATE] Run count: {state_data['run_count']}")
                
                if updated:
                    current_state['status'] = 'operational'
                    current_state['last_update'] = datetime.utcnow().isoformat()
                    
                    broadcast_payload = {**current_state}
                    await manager.broadcast(broadcast_payload)
                    logger.info(f"[BROADCAST] Sent update to {len(manager.active_connections)} clients")
                
                await asyncio.sleep(0.3)
                
    except Exception as e:
        logger.error(f"[ERROR] Graph loop failed: {e}", exc_info=True)
        current_state['status'] = 'error'
        current_state['error'] = str(e)

@app.on_event("startup")
async def startup_event():
    logger.info("[API] Starting ModelX API...")
    # Start the graph loop as background task
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
    return {
        "status": current_state.get("status"),
        "run_count": current_state.get("run_count"),
        "last_update": current_state.get("last_update"),
        "active_connections": len(manager.active_connections),
        "total_events": len(current_state.get("final_ranked_feed", []))
    }

@app.get("/api/dashboard")
def get_dashboard():
    return current_state.get("risk_dashboard_snapshot", {})

@app.get("/api/feed")
def get_feed():
    return {
        "events": current_state.get("final_ranked_feed", []),
        "total": len(current_state.get("final_ranked_feed", []))
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept and register connection (creates heartbeat task)
    await manager.connect(websocket)
    
    try:
        # Send initial state right away (best-effort)
        try:
            await websocket.send_text(json.dumps(current_state, default=str))
        except Exception as e:
            logger.debug(f"[WS] Initial send failed: {e}")
            # If initial send fails, disconnect and return
            await manager.disconnect(websocket)
            return

        # Main receive loop: we only expect 'pong' or optional client messages.
        # We don't require any client messages to keep connection alive; heartbeat handles that.
        while True:
            try:
                txt = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("[WS] Client disconnected")
                break
            except Exception as e:
                logger.debug(f"[WS] receive_text error: {e}")
                # treat as disconnect
                break

            # Handle incoming message
            try:
                payload = json.loads(txt)
                # If client responds to ping
                if isinstance(payload, dict) and payload.get("type") == "pong":
                    # Update last_pong timestamp for this connection
                    async with manager._lock:
                        meta = manager.active_connections.get(websocket)
                        if meta is not None:
                            meta['last_pong'] = datetime.utcnow()
                            meta['misses'] = 0
                    continue

                # Other client messages can be processed here if you want
                logger.debug(f"[WS] Received client message (ignored for now): {payload}")
            except json.JSONDecodeError:
                logger.debug("[WS] Received non-json message (ignored)")
                continue

    finally:
        # Ensure cleanup
        await manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
