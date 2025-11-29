import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/separator";
import { Cloud, Newspaper, TrendingUp, Users, AlertTriangle, MapPin } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface DistrictInfoPanelProps {
  district: string | null;
}

const DistrictInfoPanel = ({ district }: DistrictInfoPanelProps) => {
  if (!district) {
    return (
      <Card className="p-6 bg-card border-border h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <MapPin className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm font-mono">Select a district to view intelligence</p>
        </div>
      </Card>
    );
  }

  // Mock data - replace with actual API data
  const districtData = {
    population: "2.3M",
    weather: "Partly Cloudy, 28°C",
    alerts: [
      { type: "traffic", title: "Heavy Traffic on Main St", severity: "medium" },
      { type: "weather", title: "Rain Expected Tonight", severity: "low" },
    ],
    news: [
      { title: "New Business Park Opens", source: "Daily News", time: "2h ago" },
      { title: "Local Election Results", source: "The Island", time: "5h ago" },
      { title: "Infrastructure Development", source: "News First", time: "1d ago" },
    ],
    economic: {
      businesses: "1,234",
      growth: "+5.2%",
    },
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={district}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-6 bg-card border-border space-y-4 animate-slide-in-right">
          {/* Header */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold text-primary">{district}</h3>
              <Badge className="font-mono border border-border">DISTRICT</Badge>
            </div>
            <p className="text-xs text-muted-foreground font-mono">
              Population: {districtData.population}
            </p>
          </div>

          <Separator className="bg-border" />

          {/* Weather */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Cloud className="w-4 h-4 text-info" />
              <h4 className="font-semibold text-sm">WEATHER</h4>
            </div>
            <p className="text-sm font-mono">{districtData.weather}</p>
          </div>

          <Separator className="bg-border" />

          {/* Alerts */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-warning" />
              <h4 className="font-semibold text-sm">ACTIVE ALERTS</h4>
            </div>
            <div className="space-y-2">
              {districtData.alerts.map((alert, idx) => (
                <div key={idx} className="bg-muted/30 rounded p-2">
                  <p className="text-xs font-semibold">{alert.title}</p>
                  <Badge 
                    className={`text-xs mt-1 ${alert.severity === "high" ? "bg-destructive text-destructive-foreground" : "bg-secondary text-secondary-foreground"}`}
                  >
                    {alert.severity.toUpperCase()}
                  </Badge>
                </div>
              ))}
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Recent News */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Newspaper className="w-4 h-4 text-primary" />
              <h4 className="font-semibold text-sm">RECENT NEWS</h4>
            </div>
            <div className="space-y-2">
              {districtData.news.map((item, idx) => (
                <div key={idx} className="bg-muted/30 rounded p-2">
                  <p className="text-xs font-semibold mb-1">{item.title}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{item.source}</span>
                    <span className="text-xs font-mono text-muted-foreground">{item.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Economic */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-success" />
              <h4 className="font-semibold text-sm">ECONOMIC</h4>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/30 rounded p-2">
                <p className="text-xs text-muted-foreground">Businesses</p>
                <p className="text-lg font-bold">{districtData.economic.businesses}</p>
              </div>
              <div className="bg-muted/30 rounded p-2">
                <p className="text-xs text-muted-foreground">Growth</p>
                <p className="text-lg font-bold text-success">{districtData.economic.growth}</p>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
};

export default DistrictInfoPanel;
