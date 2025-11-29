/**
 * frontend/app/hooks/use-modelx-data.ts
 * COMPLETE - Real-time data hook with WebSocket + REST fallback + PING/PONG support
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_BASE.replace('http', 'ws') + '/ws';

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
  last_update?: string;
  error?: string;
}

export function useModelXData() {
  const [state, setState] = useState<ModelXState>({
    final_ranked_feed: [],
    risk_dashboard_snapshot: {
      logistics_friction: 0,
      compliance_volatility: 0,
      market_instability: 0,
      opportunity_index: 0,
      avg_confidence: 0,
      high_priority_count: 0,
      total_events: 0,
      last_updated: new Date().toISOString()
    },
    run_count: 0,
    status: 'initializing'
  });

  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;

  /**
   * WebSocket Connect
   */
  const connect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error('[ModelX] Max reconnection attempts reached');
      setState(prev => ({ ...prev, status: 'error', error: 'Connection failed' }));
      return;
    }

    try {
      console.log(`[ModelX] Connecting WebSocket... (attempt ${reconnectAttemptsRef.current + 1})`);
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[ModelX] ✓ WebSocket connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          /** 
           * 🔥 RESPOND TO SERVER HEARTBEAT PING 
           */
          if (data?.type === 'ping') {
            try {
              ws.send(JSON.stringify({ type: 'pong' }));
            } catch (err) {
              console.error('[ModelX] Failed to send pong:', err);
            }
            return;
          }

          /** Update state */
          setState(prevState => ({
            ...prevState,
            ...data,
            final_ranked_feed: data.final_ranked_feed || prevState.final_ranked_feed,
            risk_dashboard_snapshot: data.risk_dashboard_snapshot || prevState.risk_dashboard_snapshot
          }));

          console.log('[ModelX] State updated:', {
            events: data.final_ranked_feed?.length || 0,
            run_count: data.run_count,
            status: data.status
          });

        } catch (err) {
          console.error('[ModelX] Failed to parse message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[ModelX] WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log(`[ModelX] WebSocket closed (code: ${event.code})`);
        setIsConnected(false);
        wsRef.current = null;

        reconnectAttemptsRef.current++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);

        console.log(`[ModelX] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
        reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
      };

      wsRef.current = ws;

    } catch (err) {
      console.error('[ModelX] Connection failed:', err);
      setIsConnected(false);

      reconnectAttemptsRef.current++;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);

      reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
    }
  }, []);

  /**
   * Run initial connection
   */
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  /**
   * REST fallback when WS offline
   */
  const fetchData = useCallback(async () => {
    if (isConnected) return;

    try {
      const [dashboardRes, feedRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/dashboard`),
        fetch(`${API_BASE}/api/feed`),
        fetch(`${API_BASE}/api/status`)
      ]);

      const dashboard = await dashboardRes.json();
      const feed = await feedRes.json();
      const status = await statusRes.json();

      setState(prev => ({
        ...prev,
        risk_dashboard_snapshot: dashboard,
        final_ranked_feed: feed.events || [],
        run_count: status.run_count || prev.run_count,
        status: status.status || prev.status
      }));

      console.log('[ModelX] REST fallback updated');

    } catch (err) {
      console.error('[ModelX] REST fallback failed:', err);
      setState(prev => ({ ...prev, status: 'error', error: 'API unavailable' }));
    }
  }, [isConnected]);

  /**
   * Poll REST fallback only when WS disconnected
   */
  useEffect(() => {
    if (isConnected) return;

    const interval = setInterval(fetchData, 10000);
    fetchData();

    return () => clearInterval(interval);
  }, [isConnected, fetchData]);

  return {
    ...state,
    isConnected,
    events: state.final_ranked_feed,
    dashboard: state.risk_dashboard_snapshot,
    reconnectAttempts: reconnectAttemptsRef.current
  };
}
