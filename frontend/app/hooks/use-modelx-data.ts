/**
 * frontend/app/hooks/use-modelx-data.ts
 * Real-time data hook for ModelX platform
 */
import { useState, useEffect, useCallback } from 'react';

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
  const [ws, setWs] = useState<WebSocket | null>(null);

  // WebSocket connection
  useEffect(() => {
    let websocket: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        websocket = new WebSocket(WS_URL);

        websocket.onopen = () => {
          console.log('[ModelX] WebSocket connected');
          setIsConnected(true);
        };

        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setState(data);
          } catch (err) {
            console.error('[ModelX] Failed to parse message:', err);
          }
        };

        websocket.onerror = (error) => {
          console.error('[ModelX] WebSocket error:', error);
          setIsConnected(false);
        };

        websocket.onclose = () => {
          console.log('[ModelX] WebSocket disconnected. Reconnecting...');
          setIsConnected(false);
          
          // Reconnect after 3 seconds
          reconnectTimeout = setTimeout(() => {
            connect();
          }, 3000);
        };

        setWs(websocket);
      } catch (err) {
        console.error('[ModelX] Connection failed:', err);
        reconnectTimeout = setTimeout(() => {
          connect();
        }, 3000);
      }
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  // REST API fallback
  const fetchData = useCallback(async () => {
    if (isConnected) return; // Don't fetch if WebSocket is active

    try {
      const [dashboardRes, feedRes] = await Promise.all([
        fetch(`${API_BASE}/api/dashboard`),
        fetch(`${API_BASE}/api/feed`)
      ]);

      const dashboard = await dashboardRes.json();
      const feed = await feedRes.json();

      setState(prev => ({
        ...prev,
        risk_dashboard_snapshot: dashboard,
        final_ranked_feed: feed.events || []
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