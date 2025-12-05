import { Card } from "../ui/card";
import { AlertTriangle, TrendingUp, Cloud, Zap, Users, Building, Wifi, WifiOff } from "lucide-react";
import { Badge } from "../ui/badge";
import { useModelXData } from "../../hooks/use-modelx-data";
import { motion } from "framer-motion";

const DashboardOverview = () => {
  const { dashboard, events, isConnected, status } = useModelXData();

  // Safety check: ensure events is always an array
  const safeEvents = events || [];

  // Calculate domain-specific metrics from events
  const domainCounts = safeEvents.reduce((acc, event) => {
    acc[event.domain] = (acc[event.domain] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const riskEvents = safeEvents.filter(e => e.impact_type === 'risk');
  const opportunityEvents = safeEvents.filter(e => e.impact_type === 'opportunity');
  const criticalEvents = safeEvents.filter(e => e.severity === 'critical' || e.severity === 'high');

  const metrics = [
    {
      label: "Risk Events",
      value: riskEvents.length.toString(),
      change: criticalEvents.length > 0 ? `${criticalEvents.length} critical` : "—",
      icon: AlertTriangle,
      status: criticalEvents.length > 3 ? "warning" : "success"
    },
    {
      label: "Opportunities",
      value: opportunityEvents.length.toString(),
      change: "+Growth",
      icon: TrendingUp,
      status: "success"
    },
    {
      label: "Data Sources",
      value: Object.keys(domainCounts).length.toString(),
      change: "Active",
      icon: Zap,
      status: "info"
    },
    {
      label: "Confidence",
      value: `${Math.round(dashboard.avg_confidence * 100)}%`,
      change: "Avg Score",
      icon: Users,
      status: "success"
    },
  ];

  return (
    <div className="space-y-6">
      {/* Connection Status Banner */}
      <Card className={`p-4 ${isConnected ? 'bg-success/10 border-success/50' : 'bg-warning/10 border-warning/50'}`}>
        <div className="flex items-center gap-3">
          {isConnected ? (
            <>
              <Wifi className="w-5 h-5 text-success" />
              <div className="flex-1">
                <h3 className="font-bold text-success">SYSTEM OPERATIONAL</h3>
                <p className="text-xs text-muted-foreground">Real-time intelligence streaming • Run #{dashboard.total_events}</p>
              </div>
            </>
          ) : (
            <>
              <WifiOff className="w-5 h-5 text-warning" />
              <div className="flex-1">
                <h3 className="font-bold text-warning">RECONNECTING...</h3>
                <p className="text-xs text-muted-foreground">Attempting to restore live feed</p>
              </div>
            </>
          )}
          <Badge className="font-mono text-xs">
            {new Date(dashboard.last_updated).toLocaleTimeString()}
          </Badge>
        </div>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Card className="p-4 bg-card border-border hover:border-primary/50 transition-all">
                <div className="flex items-start justify-between mb-2">
                  <div className={`p-2 rounded bg-${metric.status}/20`}>
                    <Icon className={`w-5 h-5 text-${metric.status}`} />
                  </div>
                  <span className="text-xs font-mono text-success">{metric.change}</span>
                </div>
                <div>
                  <p className="text-2xl font-bold">{metric.value}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">{metric.label}</p>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Live Intelligence Feed */}
      <Card className="p-6 bg-card border-border">
        <h3 className="font-bold mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary" />
          LIVE INTELLIGENCE FEED
          <Badge className="ml-auto">{safeEvents.length} Events</Badge>
        </h3>
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {safeEvents.slice(0, 10).map((event, idx) => {
            const isRisk = event.impact_type === 'risk';
            const severityColor = {
              critical: 'destructive',
              high: 'warning',
              medium: 'primary',
              low: 'secondary'
            }[event.severity] || 'secondary';

            return (
              <motion.div
                key={event.event_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Card className={`p-4 bg-muted/30 border-l-4 border-l-${severityColor} hover:bg-muted/50 transition-colors`}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className={`bg-${severityColor} text-${severityColor}-foreground`}>
                          {event.severity.toUpperCase()}
                        </Badge>
                        <Badge className={isRisk ? "bg-destructive/20 text-destructive" : "bg-success/20 text-success"}>
                          {isRisk ? "⚠️ RISK" : "✨ OPPORTUNITY"}
                        </Badge>
                        <Badge className="border border-border">{event.domain}</Badge>
                      </div>
                      <p className="font-semibold text-sm mb-1">{event.summary}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Confidence: {Math.round(event.confidence * 100)}%</span>
                        <span>•</span>
                        <span className="font-mono">{new Date(event.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
          {safeEvents.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm font-mono">Initializing intelligence gathering...</p>
            </div>
          )}
        </div>
      </Card>

      {/* Operational Risk Radar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-6 bg-card border-border">
          <Cloud className="w-8 h-8 text-warning mb-3" />
          <p className="text-2xl font-bold">{Math.round(dashboard.logistics_friction * 100)}%</p>
          <p className="text-xs text-muted-foreground uppercase">Logistics Friction</p>
        </Card>
        <Card className="p-6 bg-card border-border">
          <AlertTriangle className="w-8 h-8 text-destructive mb-3" />
          <p className="text-2xl font-bold">{Math.round(dashboard.compliance_volatility * 100)}%</p>
          <p className="text-xs text-muted-foreground uppercase">Compliance Volatility</p>
        </Card>
        <Card className="p-6 bg-card border-border">
          <TrendingUp className="w-8 h-8 text-info mb-3" />
          <p className="text-2xl font-bold">{Math.round(dashboard.market_instability * 100)}%</p>
          <p className="text-xs text-muted-foreground uppercase">Market Instability</p>
        </Card>
        <Card className="p-6 bg-card border-border">
          <Building className="w-8 h-8 text-success mb-3" />
          <p className="text-2xl font-bold">{Math.round(dashboard.opportunity_index * 100)}%</p>
          <p className="text-xs text-muted-foreground uppercase">Opportunity Index</p>
        </Card>
      </div>
    </div>
  );
};

export default DashboardOverview;