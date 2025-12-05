"""
main.py
Production-Ready Real-Time Intelligence Platform Backend
- Uses combinedAgentGraph for multi-agent orchestration
- Threading for concurrent graph execution and WebSocket server
- Database-driven feed updates with polling
- Duplicate prevention
- District-based feed categorization for map display

Updated: Resilient WebSocket handling for long scraping operations (60s+ cycles)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Set
import asyncio
import json
from datetime import datetime
import sys
import os
import logging
import threading
import time
import uuid  # CRITICAL: Was missing, needed for event_id generation

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.graphs.combinedAgentGraph import graph
from src.states.combinedAgentState import CombinedAgentState
from src.storage.storage_manager import StorageManager

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

# Global state
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
    "status": "initializing",
    "first_run_complete": False  # Track first graph execution
}

# Thread-safe communication
feed_update_queue = asyncio.Queue()
seen_event_ids: Set[str] = set()  # Duplicate prevention

# Global event loop reference for cross-thread broadcasting
main_event_loop = None

# Storage manager
storage_manager = StorageManager()

# WebSocket settings - RESILIENT for long scraping operations (60s+ graph cycles)
# Increased intervals to prevent disconnections during lengthy scraping
HEARTBEAT_INTERVAL = 45.0  # Send ping every 45s (was 25s)
HEARTBEAT_TIMEOUT = 30.0   # Wait 30s for pong (was 10s) 
HEARTBEAT_MISS_THRESHOLD = 4  # Allow 4 misses (was 3) = ~3 minutes tolerance
SEND_TIMEOUT = 10.0  # Increased from 5s

class ConnectionManager:
    """Manages active WebSocket with heartbeat"""
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            meta = {
                "heartbeat_task": asyncio.create_task(self._heartbeat_loop(websocket)),
                "last_pong": datetime.utcnow(),
                "misses": 0
            }
            self.active_connections[websocket] = meta
            logger.info(f"[WebSocket] Connected. Total: {len(self.active_connections)}")

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
            logger.info(f"[WebSocket] Disconnected. Total: {len(self.active_connections)}")

    async def _send_with_timeout(self, websocket: WebSocket, message_json: str):
        try:
            await asyncio.wait_for(websocket.send_text(message_json), timeout=SEND_TIMEOUT)
            return True
        except Exception as e:
            logger.debug(f"[WebSocket] Send failed: {e}")
            return False

    async def _heartbeat_loop(self, websocket: WebSocket):
        """Per-connection heartbeat task"""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket not in self.active_connections:
                    break

                ping_payload = json.dumps({"type": "ping"})
                ok = await self._send_with_timeout(websocket, ping_payload)
                if not ok:
                    async with self._lock:
                        meta = self.active_connections.get(websocket)
                        if meta is not None:
                            meta['misses'] += 1
                else:
                    waited = 0.0
                    sleep_step = 0.5
                    pong_received = False
                    while waited < HEARTBEAT_TIMEOUT:
                        await asyncio.sleep(sleep_step)
                        waited += sleep_step
                        async with self._lock:
                            meta = self.active_connections.get(websocket)
                            if meta is None:
                                return
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

                async with self._lock:
                    meta = self.active_connections.get(websocket)
                    if meta is None:
                        return
                    if meta.get('misses', 0) >= HEARTBEAT_MISS_THRESHOLD:
                        logger.warning("[WebSocket] Miss threshold exceeded, disconnecting")
                        try:
                            await websocket.close(code=1001)
                        except Exception:
                            pass
                        await self.disconnect(websocket)
                        return

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception(f"[WebSocket] Heartbeat error: {e}")
            try:
                await self.disconnect(websocket)
            except Exception:
                pass

    async def broadcast(self, message: dict):
        """Broadcast to all connections"""
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
            logger.info("[WebSocket] Removing dead connection")
            await self.disconnect(conn)

manager = ConnectionManager()


def categorize_feed_by_district(feed: Dict[str, Any]) -> str:
    """
    Categorize feed by Sri Lankan district based on summary text.
    Returns district name or "National" if not district-specific.
    """
    summary = feed.get("summary", "").lower()
    
    # Sri Lankan districts
    districts = [
        "Colombo", "Gampaha", "Kalutara", "Kandy", "Matale", "Nuwara Eliya",
        "Galle", "Matara", "Hambantota", "Jaffna", "Kilinochchi", "Mannar",
        "Vavuniya", "Mullaitivu", "Batticaloa", "Ampara", "Trincomalee",
        "Kurunegala", "Puttalam", "Anuradhapura", "Polonnaruwa", "Badulla",
        "Moneragala", "Ratnapura", "Kegalle"
    ]
    
    for district in districts:
        if district.lower() in summary:
            return district
    
    return "National"


def run_graph_loop():
    """
    Graph execution in separate thread.
    Runs the combinedAgentGraph and stores results in database.
    """
    logger.info("="*80)
    logger.info("[GRAPH THREAD] Starting ModelX combinedAgentGraph loop")
    logger.info("="*80)
    
    initial_state = CombinedAgentState(
        domain_insights=[],
        final_ranked_feed=[],
        run_count=0,
        max_runs=999,  # Continuous mode
        route=None
    )
    
    try:
        # Note: Using synchronous invoke since we're in a thread
        for event in graph.stream(initial_state):
            logger.info(f"[GRAPH] Event nodes: {list(event.keys())}")
            
            for node_name, node_output in event.items():
                # Extract feed data
                if hasattr(node_output, 'final_ranked_feed'):
                    feeds = node_output.final_ranked_feed
                elif isinstance(node_output, dict):
                    feeds = node_output.get('final_ranked_feed', [])
                else:
                    continue
                
                if feeds:
                    logger.info(f"[GRAPH] {node_name} produced {len(feeds)} feeds")
                    
                    # FIELD_NORMALIZATION: Transform graph format to frontend format
                    for feed_item in feeds:
                        if isinstance(feed_item, dict):
                            event_data = feed_item
                        else:
                            event_data = feed_item.__dict__ if hasattr(feed_item, '__dict__') else {}
                        
                        # Normalize field names: graph uses content_summary/target_agent, frontend expects summary/domain
                        event_id = event_data.get("event_id", str(uuid.uuid4()))
                        summary = event_data.get("content_summary") or event_data.get("summary", "")
                        domain = event_data.get("target_agent") or event_data.get("domain", "unknown")
                        severity = event_data.get("severity", "medium")
                        impact_type = event_data.get("impact_type", "risk")
                        confidence = event_data.get("confidence_score", event_data.get("confidence", 0.5))
                        timestamp = event_data.get("timestamp", datetime.utcnow().isoformat())
                        
                        # Check for duplicates
                        is_dup, _, _ = storage_manager.is_duplicate(summary)
                        
                        if not is_dup:
                            try:
                                storage_manager.store_event(
                                    event_id=event_id,
                                    summary=summary,
                                    domain=domain,
                                    severity=severity,
                                    impact_type=impact_type,
                                    confidence_score=confidence
                                )
                                logger.info(f"[GRAPH] Stored new feed: {summary[:60]}...")
                            except Exception as storage_error:
                                logger.warning(f"[GRAPH] Storage error (continuing): {storage_error}")
                            
                            # DIRECT_BROADCAST_FIX: Set first_run_complete and broadcast
                            if not current_state.get('first_run_complete'):
                                current_state['first_run_complete'] = True
                                current_state['status'] = 'operational'
                                logger.info("[GRAPH] FIRST RUN COMPLETE - Broadcasting to frontend!")
                                
                                # Trigger broadcast from sync thread to async loop
                                if main_event_loop:
                                    asyncio.run_coroutine_threadsafe(
                                        manager.broadcast(current_state),
                                        main_event_loop
                                    )
                
                # Small delay to prevent CPU overload
                time.sleep(0.3)
                
    except Exception as e:
        logger.error(f"[GRAPH THREAD] Error: {e}", exc_info=True)


async def database_polling_loop():
    """
    Polls database for new feeds and broadcasts via WebSocket.
    Runs concurrently with graph thread.
    """
    global current_state
    last_check = datetime.utcnow()
    
    logger.info("[DB_POLLER] Starting database polling loop")
    
    while True:
        try:
            await asyncio.sleep(2.0)  # Poll every 2 seconds
            
            # Get new feeds since last check
            new_feeds = storage_manager.get_feeds_since(last_check)
            last_check = datetime.utcnow()
            
            if new_feeds:
                logger.info(f"[DB_POLLER] Found {len(new_feeds)} new feeds")
                
                # Filter duplicates (by event_id)
                unique_feeds = []
                for feed in new_feeds:
                    event_id = feed.get("event_id")
                    if event_id and event_id not in seen_event_ids:
                        seen_event_ids.add(event_id)
                        
                        # Add district categorization for map
                        feed["district"] = categorize_feed_by_district(feed)
                        unique_feeds.append(feed)
                
                if unique_feeds:
                    # Update current state
                    current_state['final_ranked_feed'] = unique_feeds + current_state.get('final_ranked_feed', [])
                    current_state['final_ranked_feed'] = current_state['final_ranked_feed'][:100]  # Keep last 100
                    current_state['status'] = 'operational'
                    current_state['last_update'] = datetime.utcnow().isoformat()
                    
                    # Mark first run as complete (frontend loading screen can now hide)
                    if not current_state.get('first_run_complete'):
                        current_state['first_run_complete'] = True
                        logger.info("[DB_POLLER] First graph run complete! Frontend loading screen can now hide.")
                    
                    # Broadcast to WebSocket clients
                    await manager.broadcast(current_state)
                    logger.info(f"[DB_POLLER] Broadcasted {len(unique_feeds)} unique feeds")
            
        except Exception as e:
            logger.error(f"[DB_POLLER] Error: {e}")



@app.on_event("startup")
async def startup_event():
    global main_event_loop
    main_event_loop = asyncio.get_event_loop()
    
    logger.info("[API] Starting ModelX API...")
    
    # Start graph execution in separate thread
    graph_thread = threading.Thread(target=run_graph_loop, daemon=True)
    graph_thread.start()
    logger.info("[API] Graph thread started")
    
    # Start database polling loop
    asyncio.create_task(database_polling_loop())
    logger.info("[API] Database polling started")


@app.get("/")
def read_root():
    return {
        "service": "ModelX Intelligence Platform",
        "status": current_state.get("status"),
        "version": "2.0.0 (Database-Driven)"
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
    """Get current feed from memory"""
    return {
        "events": current_state.get("final_ranked_feed", []),
        "total": len(current_state.get("final_ranked_feed", []))
    }


@app.get("/api/feeds")
def get_feeds_from_db(limit: int = 100):
    """Get feeds directly from database (for initial load)"""
    try:
        feeds = storage_manager.get_recent_feeds(limit=limit)
        
        # FIELD_NORMALIZATION + district categorization
        normalized_feeds = []
        for feed in feeds:
            # Ensure frontend-compatible field names
            normalized = {
                "event_id": feed.get("event_id"),
                "summary": feed.get("summary", ""),
                "domain": feed.get("domain", "unknown"),
                "severity": feed.get("severity", "medium"),
                "impact_type": feed.get("impact_type", "risk"),
                "confidence": feed.get("confidence", 0.5),
                "timestamp": feed.get("timestamp"),
                "district": categorize_feed_by_district(feed)
            }
            normalized_feeds.append(normalized)
        
        return {
            "events": normalized_feeds,
            "total": len(normalized_feeds),
            "source": "database"
        }
    except Exception as e:
        logger.error(f"[API] Error fetching feeds: {e}")
        return {"events": [], "total": 0, "error": str(e)}


@app.get("/api/feeds/by_district/{district}")
def get_feeds_by_district(district: str, limit: int = 50):
    """Get feeds for specific district"""
    try:
        all_feeds = storage_manager.get_recent_feeds(limit=200)
        
        # Filter by district
        district_feeds = []
        for feed in all_feeds:
            feed["district"] = categorize_feed_by_district(feed)
            if feed["district"].lower() == district.lower():
                district_feeds.append(feed)
                if len(district_feeds) >= limit:
                    break
        
        return {
            "district": district,
            "events": district_feeds,
            "total": len(district_feeds)
        }
    except Exception as e:
        logger.error(f"[API] Error fetching district feeds: {e}")
        return {"events": [], "total": 0, "error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Send initial state
        try:
            await websocket.send_text(json.dumps(current_state, default=str))
        except Exception as e:
            logger.debug(f"[WS] Initial send failed: {e}")
            await manager.disconnect(websocket)
            return

        # Main receive loop
        while True:
            try:
                txt = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("[WS] Client disconnected")
                break
            except Exception as e:
                logger.debug(f"[WS] Receive error: {e}")
                break

            # Handle pong responses
            try:
                payload = json.loads(txt)
                if isinstance(payload, dict) and payload.get("type") == "pong":
                    async with manager._lock:
                        meta = manager.active_connections.get(websocket)
                        if meta is not None:
                            meta['last_pong'] = datetime.utcnow()
                            meta['misses'] = 0
                    continue
            except json.JSONDecodeError:
                continue

    finally:
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    import uuid
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
