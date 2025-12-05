/**
 * frontend/app/hooks/use-modelx-data.ts
 * Real-time data hook for ModelX platform
 * 
 * FIXED: State now MERGES instead of REPLACES when receiving WebSocket updates.
 * This prevents data from disappearing when partial updates arrive.
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_BASE.replace('http', 'ws') + '/ws';

// Timeouts for resilient connection
const RECONNECT_DELAY = 3000;
const MAX_LOADING_TIME = 120000; // 2 minutes max loading time
const INITIAL_FETCH_DELAY = 2000; // Fetch from REST after 2s if no WS data

export interface ModelXEvent {
  event_id: string;
  domain: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  impact_type: 'risk' | 'opportunity';
  summary: string;
  confidence: number;
  timestamp: string;
}

export interface RiskDashboard {
  logistics_friction: number;
  compliance_volatility: number;
  market_instability: number;
  opportunity_index: number;
  avg_confidence: number;
  high_priority_count: number;
  total_events: number;
  last_updated: string;
}

export interface ModelXState {
  final_ranked_feed: ModelXEvent[];
  risk_dashboard_snapshot: RiskDashboard;
  run_count: number;
  status: 'initializing' | 'operational' | 'error';
  first_run_complete?: boolean;
  last_update?: string;
}

const DEFAULT_DASHBOARD: RiskDashboard = {
  logistics_friction: 0,
  compliance_volatility: 0,
  market_instability: 0,
  opportunity_index: 0,
  avg_confidence: 0,
  high_priority_count: 0,
  total_events: 0,
  last_updated: new Date().toISOString()
};

export function useModelXData() {
  const [state, setState] = useState<ModelXState>({
    final_ranked_feed: [],
    risk_dashboard_snapshot: DEFAULT_DASHBOARD,
    run_count: 0,
    status: 'initializing',
    first_run_complete: false
  });

  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const initialFetchDoneRef = useRef(false);

  // Fetch initial data from REST API (for faster initial load)
  const fetchInitialData = useCallback(async () => {
    if (initialFetchDoneRef.current) return;

    try {
      console.log('[ModelX] Fetching initial data from REST API...');
      const feedRes = await fetch(`${API_BASE}/api/feeds`);
      const feedData = await feedRes.json();

      if (feedData.events && feedData.events.length > 0) {
        console.log(`[ModelX] Loaded ${feedData.events.length} existing feeds from database`);
        initialFetchDoneRef.current = true;

        setState(prev => ({
          ...prev,
          final_ranked_feed: feedData.events,
          status: 'operational',
          first_run_complete: true
        }));
      }
    } catch (err) {
      console.warn('[ModelX] Initial fetch failed, waiting for WebSocket:', err);
    }
  }, []);

  // WebSocket connection with ping/pong handling
  useEffect(() => {
    let websocket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        console.log('[ModelX] Connecting to WebSocket:', WS_URL);
        websocket = new WebSocket(WS_URL);

        websocket.onopen = () => {
          console.log('[ModelX] WebSocket connected');
          setIsConnected(true);
        };

        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // CRITICAL: Respond to server ping with pong
            if (data.type === 'ping') {
              console.log('[ModelX] Received ping, sending pong');
              if (websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ type: 'pong' }));
              }
              return;
            }

            // FIXED: MERGE state instead of replacing!
            // This preserves existing data when partial updates arrive
            setState(prev => {
              // Only update fields that are actually present and non-empty in incoming data
              const newFeed = (data.final_ranked_feed && data.final_ranked_feed.length > 0)
                ? data.final_ranked_feed
                : prev.final_ranked_feed;

              const newDashboard = data.risk_dashboard_snapshot || prev.risk_dashboard_snapshot;

              // Determine status - once operational, stay operational unless error
              let newStatus = prev.status;
              if (data.status === 'error') {
                newStatus = 'error';
              } else if (data.status === 'operational' || newFeed.length > 0) {
                newStatus = 'operational';
              }

              // Once first_run_complete is true, it stays true
              const newFirstRunComplete = prev.first_run_complete || data.first_run_complete || newFeed.length > 0;

              console.log(`[ModelX] State merge: feed=${newFeed.length} events, status=${newStatus}, first_run=${newFirstRunComplete}`);

              return {
                final_ranked_feed: newFeed,
                risk_dashboard_snapshot: newDashboard,
                run_count: data.run_count ?? prev.run_count,
                status: newStatus,
                first_run_complete: newFirstRunComplete,
                last_update: data.last_update || new Date().toISOString()
              };
            });

            // If we received data with feeds, mark initial fetch as done
            if (data.final_ranked_feed && data.final_ranked_feed.length > 0) {
              initialFetchDoneRef.current = true;
            }
          } catch (err) {
            console.error('[ModelX] Failed to parse message:', err);
          }
        };

        websocket.onerror = (error) => {
          console.error('[ModelX] WebSocket error:', error);
          setIsConnected(false);
        };

        websocket.onclose = () => {
          console.log('[ModelX] WebSocket disconnected. Reconnecting in 3s...');
          setIsConnected(false);

          // Reconnect after delay
          reconnectTimeout = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        };

        wsRef.current = websocket;
      } catch (err) {
        console.error('[ModelX] Connection failed:', err);
        reconnectTimeout = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY);
      }
    };

    connect();

    // Fetch initial data from REST API after a short delay
    const initialFetchTimeout = setTimeout(() => {
      fetchInitialData();
    }, INITIAL_FETCH_DELAY);

    // Safety timeout: Force loading complete after MAX_LOADING_TIME
    loadingTimeoutRef.current = setTimeout(() => {
      setState(prev => {
        if (!prev.first_run_complete) {
          console.log('[ModelX] Loading timeout reached, forcing operational state');
          return {
            ...prev,
            status: 'operational',
            first_run_complete: true
          };
        }
        return prev;
      });
    }, MAX_LOADING_TIME);

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (initialFetchTimeout) clearTimeout(initialFetchTimeout);
      if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
      if (websocket) {
        websocket.close();
      }
    };
  }, [fetchInitialData]);

  // REST API fallback polling (when WebSocket disconnected)
  const fetchData = useCallback(async () => {
    if (isConnected) return; // Don't fetch if WebSocket is active

    try {
      const [dashboardRes, feedRes] = await Promise.all([
        fetch(`${API_BASE}/api/dashboard`),
        fetch(`${API_BASE}/api/feeds`)
      ]);

      const dashboard = await dashboardRes.json();
      const feed = await feedRes.json();

      setState(prev => ({
        ...prev,
        risk_dashboard_snapshot: dashboard || prev.risk_dashboard_snapshot,
        final_ranked_feed: (feed.events && feed.events.length > 0) ? feed.events : prev.final_ranked_feed,
        status: (feed.events && feed.events.length > 0) ? 'operational' : prev.status,
        first_run_complete: prev.first_run_complete || (feed.events && feed.events.length > 0)
      }));
    } catch (err) {
      console.error('[ModelX] REST API fetch failed:', err);
    }
  }, [isConnected]);

  // Fallback polling if WebSocket fails
  useEffect(() => {
    if (isConnected) return;

    const interval = setInterval(fetchData, 5000);
    fetchData(); // Initial fetch

    return () => clearInterval(interval);
  }, [isConnected, fetchData]);

  return {
    ...state,
    isConnected,
    events: state.final_ranked_feed,
    dashboard: state.risk_dashboard_snapshot
  };
}