import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Newspaper, Cloud, TrendingUp, AlertTriangle, FileText, Radio } from "lucide-react";
import { useModelXData, ModelXEvent } from "../../hooks/use-modelx-data";
import { motion } from "framer-motion";

const IntelligenceFeed = () => {
  const { events, isConnected } = useModelXData();

  // Filter events by domain
  const allEvents = events;
  const newsEvents = events.filter(e => e.domain === 'social' || e.domain === 'intelligence');
  const politicalEvents = events.filter(e => e.domain === 'political');
  const weatherEvents = events.filter(e => e.domain === 'weather' || e.domain === 'meteorological');
  const economicEvents = events.filter(e => e.domain === 'economical' || e.domain === 'market');

  const renderEventCard = (item: ModelXEvent, idx: number) => {
    const isRisk = item.impact_type === 'risk';
    
    // Type-safe severity color mapping
    const severityColorMap: Record<string, string> = {
      critical: 'destructive',
      high: 'warning',
      medium: 'primary',
      low: 'secondary'
    };
    const severityColor = severityColorMap[item.severity] || 'secondary';

    // Type-safe domain icon mapping
    const domainIconMap: Record<string, React.ComponentType<any>> = {
      social: Newspaper,
      political: FileText,
      weather: Cloud,
      meteorological: Cloud,
      economical: TrendingUp,
      market: TrendingUp,
      intelligence: Radio
    };
    const Icon = domainIconMap[item.domain] || Radio;

    return (
      <motion.div
        key={item.event_id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: idx * 0.05 }}
      >
        <Card className={`p-4 bg-muted/30 border-l-4 hover:bg-muted/50 transition-colors ${
          severityColor === 'destructive' ? 'border-l-destructive' :
          severityColor === 'warning' ? 'border-l-warning' :
          severityColor === 'primary' ? 'border-l-primary' :
          'border-l-secondary'
        }`}>
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4" />
                <Badge className={
                  severityColor === 'destructive' ? 'bg-destructive text-destructive-foreground' :
                  severityColor === 'warning' ? 'bg-warning text-warning-foreground' :
                  severityColor === 'primary' ? 'bg-primary text-primary-foreground' :
                  'bg-secondary text-secondary-foreground'
                }>
                  {item.severity.toUpperCase()}
                </Badge>
                <Badge className={isRisk ? "bg-destructive/20 text-destructive" : "bg-success/20 text-success"}>
                  {isRisk ? "⚠️ RISK" : "✨ OPP"}
                </Badge>
                <Badge className="border border-border">{item.domain}</Badge>
              </div>
              <h3 className="font-bold text-sm mb-1">{item.summary}</h3>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Confidence: {Math.round(item.confidence * 100)}%</span>
                <span>•</span>
                <span className="font-mono">{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    );
  };

  return (
    <div className="space-y-6">
      <Card className="p-6 bg-card border-border">
        <div className="flex items-center gap-2 mb-4">
          <Radio className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold">INTELLIGENCE FEED</h2>
          <span className="ml-auto text-xs font-mono text-muted-foreground">
            {isConnected ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
                Live
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-warning"></span>
                Reconnecting...
              </span>
            )}
          </span>
        </div>

        <Tabs defaultValue="all" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-4">
            <TabsTrigger value="all">
              ALL ({allEvents.length})
            </TabsTrigger>
            <TabsTrigger value="news">
              NEWS ({newsEvents.length})
            </TabsTrigger>
            <TabsTrigger value="political">
              POLITICAL ({politicalEvents.length})
            </TabsTrigger>
            <TabsTrigger value="weather">
              WEATHER ({weatherEvents.length})
            </TabsTrigger>
            <TabsTrigger value="economic">
              ECONOMIC ({economicEvents.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-3 max-h-[600px] overflow-y-auto">
            {allEvents.length > 0 ? (
              allEvents.map((item, idx) => renderEventCard(item, idx))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Radio className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm font-mono">Waiting for intelligence data...</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="news" className="space-y-3 max-h-[600px] overflow-y-auto">
            {newsEvents.length > 0 ? (
              newsEvents.map((item, idx) => renderEventCard(item, idx))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Newspaper className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No news events yet</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="political" className="space-y-3 max-h-[600px] overflow-y-auto">
            {politicalEvents.length > 0 ? (
              politicalEvents.map((item, idx) => renderEventCard(item, idx))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No political updates yet</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="weather" className="space-y-3 max-h-[600px] overflow-y-auto">
            {weatherEvents.length > 0 ? (
              weatherEvents.map((item, idx) => renderEventCard(item, idx))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Cloud className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No weather alerts yet</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="economic" className="space-y-3 max-h-[600px] overflow-y-auto">
            {economicEvents.length > 0 ? (
              economicEvents.map((item, idx) => renderEventCard(item, idx))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No economic data yet</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
};

export default IntelligenceFeed;