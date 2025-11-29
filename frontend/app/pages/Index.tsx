'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import DashboardOverview from "../components/dashboard/DashboardOverview";
import MapView from "../components/map/MapView";
import IntelligenceFeed from "../components/intelligence/IntelligenceFeed";
import StockPredictions from "../components/dashboard/StockPredictions";
import { Activity, Map, Radio, BarChart3 } from "lucide-react";

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-primary rounded flex items-center justify-center">
                  <Activity className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-foreground">MODEL<span className="text-primary">X</span></h1>
                  <p className="text-xs text-muted-foreground font-mono">SITUATIONAL AWARENESS</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="status-active">
                <span className="text-xs font-mono text-success">OPERATIONAL</span>
              </div>
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
              <div className="bg-card border border-border rounded p-6">
                <h2 className="text-lg font-bold mb-4">Market Analytics</h2>
                <p className="text-muted-foreground">Real-time market intelligence and anomaly detection coming soon...</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Index;
