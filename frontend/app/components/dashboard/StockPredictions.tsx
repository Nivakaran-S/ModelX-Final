import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import { motion } from "framer-motion";

interface Stock {
  symbol: string;
  name: string;
  current: number;
  predicted: number;
  change: number;
  changePercent: number;
  volume: string;
}

const StockPredictions = () => {
  // Mock data - replace with real API
  const stocks: Stock[] = [
    {
      symbol: "JKH.N0000",
      name: "John Keells Holdings",
      current: 145.50,
      predicted: 148.20,
      change: 2.70,
      changePercent: 1.86,
      volume: "1.2M"
    },
    {
      symbol: "COMB.N0000",
      name: "Commercial Bank",
      current: 89.75,
      predicted: 87.30,
      change: -2.45,
      changePercent: -2.73,
      volume: "856K"
    },
    {
      symbol: "HNB.N0000",
      name: "Hatton National Bank",
      current: 178.20,
      predicted: 182.50,
      change: 4.30,
      changePercent: 2.41,
      volume: "632K"
    },
    {
      symbol: "SAMP.N0000",
      name: "Sampath Bank",
      current: 95.80,
      predicted: 94.10,
      change: -1.70,
      changePercent: -1.77,
      volume: "445K"
    },
    {
      symbol: "DIST.N0000",
      name: "Distilleries Company",
      current: 32.40,
      predicted: 33.80,
      change: 1.40,
      changePercent: 4.32,
      volume: "1.8M"
    },
    {
      symbol: "DIAL.N0000",
      name: "Dialog Axiata",
      current: 12.30,
      predicted: 12.10,
      change: -0.20,
      changePercent: -1.63,
      volume: "2.3M"
    },
  ];

  return (
    <Card className="p-6 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-success" />
          <h2 className="text-lg font-bold">STOCK PREDICTIONS - CSE</h2>
        </div>
        <Badge className="font-mono text-xs border">
          LIVE AI FORECAST
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {stocks.map((stock, idx) => {
          const isPositive = stock.change > 0;
          
          return (
            <motion.div
              key={stock.symbol}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Card className="p-4 bg-muted/30 border-border hover:border-primary/50 transition-all">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-sm">{stock.symbol}</h3>
                    <p className="text-xs text-muted-foreground">{stock.name}</p>
                  </div>
                  <Badge 
                    className={`font-mono text-xs ${isPositive ? "bg-primary text-primary-foreground" : "bg-destructive text-destructive-foreground"}`}
                  >
                    {isPositive ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                    {isPositive ? "+" : ""}{stock.changePercent.toFixed(2)}%
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Current</p>
                    <p className="text-lg font-bold font-mono">
                      LKR {stock.current.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Predicted</p>
                    <p className={`text-lg font-bold font-mono ${isPositive ? "text-success" : "text-destructive"}`}>
                      LKR {stock.predicted.toFixed(2)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                  <span className="text-xs text-muted-foreground">
                    Vol: {stock.volume}
                  </span>
                  <span className={`text-xs font-bold font-mono ${isPositive ? "text-success" : "text-destructive"}`}>
                    {isPositive ? "+" : ""}{stock.change.toFixed(2)}
                  </span>
                </div>

                {/* Prediction confidence bar */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-mono">{Math.floor(75 + Math.random() * 20)}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-primary"
                      initial={{ width: 0 }}
                      animate={{ width: `${75 + Math.random() * 20}%` }}
                      transition={{ duration: 1, delay: idx * 0.1 }}
                    />
                  </div>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-4 p-3 bg-muted/20 rounded border border-border">
        <p className="text-xs text-muted-foreground font-mono">
          <span className="text-warning font-bold">⚠ DISCLAIMER:</span> Predictions are AI-generated based on historical patterns and market indicators. Not financial advice.
        </p>
      </div>
    </Card>
  );
};

export default StockPredictions;
