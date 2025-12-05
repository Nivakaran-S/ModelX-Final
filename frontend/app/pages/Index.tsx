'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import DashboardOverview from "../components/dashboard/DashboardOverview";
import MapView from "../components/map/MapView";
import IntelligenceFeed from "../components/intelligence/IntelligenceFeed";
import StockPredictions from "../components/dashboard/StockPredictions";
import LoadingScreen from "../components/LoadingScreen";
import { Activity, Map, Radio, BarChart3, Zap } from "lucide-react";
import { useModelXData } from "../hooks/use-modelx-data";
import { Badge } from "../components/ui/badge";

const Index = () => {
  const { status, run_count, isConnected, first_run_complete, events } = useModelXData();

  // Show loading screen until:
  // 1. first_run_complete is true, OR
  // 2. We have existing events from REST API (faster initial load)
  // This ensures the loading screen disappears once ANY data is available
  const isLoading = status === 'initializing' && !first_run_complete && (!events || events.length === 0);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-primary rounded flex items-center justify-center">
                  <Activity className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-foreground">
                    MODEL<span className="text-primary">X</span>
                  </h1>
                  <p className="text-xs text-muted-foreground font-mono">SITUATIONAL AWARENESS</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {/* Connection Status */}
              {isConnected ? (
                <Badge className="bg-success/20 text-success flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
                  OPERATIONAL
                </Badge>
              ) : (
                <Badge className="bg-warning/20 text-warning flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-warning animate-pulse"></span>
                  RECONNECTING
                </Badge>
              )}

              {/* System Status */}
              <Badge className="border border-border flex items-center gap-2">
                <Zap className="w-3 h-3" />
                Run #{run_count}
              </Badge>

              {/* Time */}
              <div className="text-xs font-mono text-muted-foreground">
                {new Date().toLocaleString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false
                })} HRS
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-6">
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-6 bg-card border border-border">
            <TabsTrigger value="overview" className="data-ready gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">OVERVIEW</span>
            </TabsTrigger>
            <TabsTrigger value="map" className="data-ready gap-2">
              <Map className="w-4 h-4" />
              <span className="hidden sm:inline">TERRITORY MAP</span>
            </TabsTrigger>
            <TabsTrigger value="intelligence" className="data-ready gap-2">
              <Radio className="w-4 h-4" />
              <span className="hidden sm:inline">INTEL FEED</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="data-ready gap-2">
              <Activity className="w-4 h-4" />
              <span className="hidden sm:inline">ANALYTICS</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 animate-fade-in">
            <DashboardOverview />
            <StockPredictions />
          </TabsContent>

          <TabsContent value="map" className="animate-fade-in">
            <MapView />
          </TabsContent>

          <TabsContent value="intelligence" className="animate-fade-in">
            <IntelligenceFeed />
          </TabsContent>

          <TabsContent value="analytics" className="animate-fade-in">
            <div className="grid gap-6">
              <StockPredictions />
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Index;