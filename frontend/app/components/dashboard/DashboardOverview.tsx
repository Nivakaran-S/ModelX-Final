import { Card } from "../ui/card";
import { AlertTriangle, TrendingUp, Cloud, Zap, Users, Building } from "lucide-react";
import { Badge } from "../ui/badge";

const DashboardOverview = () => {
  const criticalAlerts = [
    { type: "weather", title: "Heavy Rainfall Alert", district: "Colombo", severity: "high", time: "14:23" },
    { type: "traffic", title: "Road Closure A9", district: "Jaffna", severity: "medium", time: "13:45" },
    { type: "political", title: "Gazette Notification", district: "Nationwide", severity: "info", time: "12:00" },
  ];

  const metrics = [
    { label: "Active Alerts", value: "12", change: "+3", icon: AlertTriangle, status: "warning" },
    { label: "Districts Monitored", value: "25", change: "—", icon: Building, status: "success" },
    { label: "Data Sources", value: "47", change: "+2", icon: Zap, status: "info" },
    { label: "Active Users", value: "1,234", change: "+45", icon: Users, status: "success" },
  ];

  const recentEvents = [
    { title: "Parliament Session Concluded", category: "Political", time: "2 hrs ago" },
    { title: "CSE Market Update: High Volume", category: "Economic", time: "3 hrs ago" },
    { title: "Monsoon Warning Extended", category: "Weather", time: "4 hrs ago" },
    { title: "New Business Registration Spike", category: "Business", time: "5 hrs ago" },
  ];

  return (
    <div className="space-y-6">
      {/* Critical Alerts Banner */}
      <Card className="bg-destructive/10 border-destructive/50 p-4">
        <div className="flex items-center gap-3 mb-3">
          <AlertTriangle className="w-5 h-5 text-destructive" />
          <h3 className="font-bold text-destructive">CRITICAL ALERTS</h3>
        </div>
        <div className="grid gap-2">
          {criticalAlerts.map((alert, idx) => (
            <div key={idx} className="flex items-center justify-between bg-background/50 rounded p-3">
              <div className="flex-1">
                <p className="font-semibold text-sm">{alert.title}</p>
                <p className="text-xs text-muted-foreground">{alert.district}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge className={alert.severity === "high" ? "bg-destructive text-destructive-foreground" : alert.severity === "medium" ? "bg-yellow-500 text-white" : "bg-blue-500 text-white"}>
                  {alert.severity.toUpperCase()}
                </Badge>
                <span className="text-xs font-mono text-muted-foreground">{alert.time}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <Card key={idx} className="p-4 bg-card border-border hover:border-primary/50 transition-all">
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
          );
        })}
      </div>

      {/* Recent Activity */}
      <Card className="p-6 bg-card border-border">
        <h3 className="font-bold mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary" />
          RECENT ACTIVITY
        </h3>
        <div className="space-y-3">
          {recentEvents.map((event, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-muted/30 rounded hover:bg-muted/50 transition-colors">
              <div>
                <p className="font-semibold text-sm">{event.title}</p>
                <p className="text-xs text-muted-foreground">{event.category}</p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">{event.time}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6 bg-card border-border">
          <Cloud className="w-8 h-8 text-info mb-3" />
          <p className="text-2xl font-bold">72%</p>
          <p className="text-xs text-muted-foreground uppercase">Weather Clear</p>
        </Card>
        <Card className="p-6 bg-card border-border">
          <TrendingUp className="w-8 h-8 text-success mb-3" />
          <p className="text-2xl font-bold">+4.2%</p>
          <p className="text-xs text-muted-foreground uppercase">Market Activity</p>
        </Card>
        <Card className="p-6 bg-card border-border">
          <AlertTriangle className="w-8 h-8 text-warning mb-3" />
          <p className="text-2xl font-bold">3</p>
          <p className="text-xs text-muted-foreground uppercase">Active Warnings</p>
        </Card>
      </div>
    </div>
  );
};

export default DashboardOverview;
