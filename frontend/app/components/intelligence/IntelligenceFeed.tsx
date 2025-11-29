import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Newspaper, Cloud, TrendingUp, AlertTriangle, FileText, Radio } from "lucide-react";

const IntelligenceFeed = () => {
  const newsItems = [
    { 
      title: "Parliament Passes New Digital Economy Act",
      source: "Daily News",
      category: "Political",
      time: "15 min ago",
      priority: "high",
      district: "Colombo"
    },
    {
      title: "Heavy Monsoon Affects Northern Provinces",
      source: "MeteoLK",
      category: "Weather",
      time: "1 hour ago",
      priority: "critical",
      district: "Jaffna"
    },
    {
      title: "CSE All Share Index Rises 2.3%",
      source: "Business Today",
      category: "Economic",
      time: "2 hours ago",
      priority: "medium",
      district: "Colombo"
    },
  ];

  const politicalUpdates = [
    {
      title: "Extraordinary Gazette Notification No. 2024/45",
      description: "New export regulations for apparel sector",
      time: "3 hours ago",
      type: "gazette"
    },
    {
      title: "Parliament Session Summary",
      description: "Budget allocation for infrastructure development",
      time: "Yesterday",
      type: "parliament"
    },
  ];

  const weatherAlerts = [
    {
      title: "Heavy Rainfall Warning",
      districts: ["Colombo", "Gampaha", "Kalutara"],
      severity: "high",
      validUntil: "18:00 today"
    },
    {
      title: "Strong Wind Advisory",
      districts: ["Jaffna", "Mannar"],
      severity: "medium",
      validUntil: "22:00 today"
    },
  ];

  return (
    <div className="space-y-6">
      <Card className="p-6 bg-card border-border">
        <div className="flex items-center gap-2 mb-4">
          <Radio className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold">INTELLIGENCE FEED</h2>
          <span className="ml-auto text-xs font-mono text-muted-foreground">
            Real-time updates
          </span>
        </div>

        <Tabs defaultValue="all" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-4">
            <TabsTrigger value="all">ALL</TabsTrigger>
            <TabsTrigger value="news">NEWS</TabsTrigger>
            <TabsTrigger value="political">POLITICAL</TabsTrigger>
            <TabsTrigger value="weather">WEATHER</TabsTrigger>
            <TabsTrigger value="economic">ECONOMIC</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-3">
            {newsItems.map((item, idx) => (
              <Card key={idx} className="p-4 bg-muted/30 border-l-4 border-l-primary hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className={
                        item.priority === "critical" ? "bg-destructive text-destructive-foreground" : 
                        item.priority === "high" ? "bg-primary text-primary-foreground" : 
                        "bg-secondary text-secondary-foreground"
                      }>
                        {item.priority.toUpperCase()}
                      </Badge>
                      <Badge className="border border-border">{item.category}</Badge>
                      <span className="text-xs font-mono text-muted-foreground">{item.district}</span>
                    </div>
                    <h3 className="font-bold text-sm mb-1">{item.title}</h3>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.source}</span>
                      <span>•</span>
                      <span className="font-mono">{item.time}</span>
                    </div>
                  </div>
                  <Newspaper className="w-5 h-5 text-primary opacity-50" />
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="news" className="space-y-3">
            {newsItems.filter(item => item.category !== "Political" && item.category !== "Weather").map((item, idx) => (
              <Card key={idx} className="p-4 bg-muted/30">
                <h3 className="font-bold text-sm mb-2">{item.title}</h3>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{item.source}</span>
                  <span>•</span>
                  <span className="font-mono">{item.time}</span>
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="political" className="space-y-3">
            {politicalUpdates.map((item, idx) => (
              <Card key={idx} className="p-4 bg-muted/30 border-l-4 border-l-info">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-info mt-1" />
                  <div className="flex-1">
                    <h3 className="font-bold text-sm mb-1">{item.title}</h3>
                    <p className="text-xs text-muted-foreground mb-2">{item.description}</p>
                    <span className="text-xs font-mono text-muted-foreground">{item.time}</span>
                  </div>
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="weather" className="space-y-3">
            {weatherAlerts.map((alert, idx) => (
              <Card key={idx} className={`p-4 ${
                alert.severity === "high" ? "bg-destructive/20 border-destructive" : "bg-warning/20 border-warning"
              }`}>
                <div className="flex items-start gap-3">
                  <Cloud className={`w-5 h-5 ${
                    alert.severity === "high" ? "text-destructive" : "text-warning"
                  } mt-1`} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-bold text-sm">{alert.title}</h3>
                      <Badge className={alert.severity === "high" ? "bg-destructive text-destructive-foreground" : "bg-default text-default-foreground"}>
                        {alert.severity.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs mb-2">
                      <span className="font-semibold">Districts:</span> {alert.districts.join(", ")}
                    </p>
                    <p className="text-xs font-mono text-muted-foreground">Valid until: {alert.validUntil}</p>
                  </div>
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="economic" className="space-y-3">
            {newsItems.filter(item => item.category === "Economic").map((item, idx) => (
              <Card key={idx} className="p-4 bg-muted/30 border-l-4 border-l-success">
                <div className="flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-success mt-1" />
                  <div className="flex-1">
                    <h3 className="font-bold text-sm mb-1">{item.title}</h3>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.source}</span>
                      <span>•</span>
                      <span className="font-mono">{item.time}</span>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
};

export default IntelligenceFeed;
