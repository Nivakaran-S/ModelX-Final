import { motion } from "framer-motion";

interface SriLankaMapProps {
  selectedDistrict: string | null;
  onDistrictSelect: (district: string) => void;
  alertCounts?: Record<string, number>;
}

const SriLankaMap = ({ selectedDistrict, onDistrictSelect, alertCounts = {} }: SriLankaMapProps) => {
  const districts = [
    { name: "Jaffna", path: "M 180 10 L 200 8 L 220 12 L 235 25 L 230 40 L 215 45 L 195 42 L 175 35 L 170 20 Z" },
    { name: "Kilinochchi", path: "M 175 35 L 195 42 L 215 45 L 230 50 L 225 65 L 205 70 L 185 68 L 170 55 Z" },
    { name: "Mannar", path: "M 145 55 L 170 55 L 185 68 L 180 85 L 165 95 L 145 90 L 135 75 Z" },
    { name: "Vavuniya", path: "M 170 55 L 185 68 L 205 70 L 220 78 L 218 95 L 200 100 L 180 98 L 165 95 L 170 85 Z" },
    { name: "Mullaitivu", path: "M 220 50 L 245 55 L 260 68 L 258 85 L 240 92 L 220 78 L 215 65 Z" },
    { name: "Trincomalee", path: "M 240 92 L 258 85 L 272 105 L 275 130 L 268 145 L 250 138 L 235 125 L 230 105 Z" },
    { name: "Anuradhapura", path: "M 145 90 L 165 95 L 180 98 L 200 100 L 210 115 L 205 135 L 185 145 L 165 140 L 150 125 L 145 105 Z" },
    { name: "Polonnaruwa", path: "M 210 115 L 230 105 L 250 138 L 248 158 L 230 165 L 210 160 L 205 135 Z" },
    { name: "Puttalam", path: "M 135 125 L 150 125 L 165 140 L 168 160 L 160 178 L 145 175 L 130 160 L 128 140 Z" },
    { name: "Kurunegala", path: "M 150 125 L 165 140 L 185 145 L 195 165 L 188 185 L 170 190 L 155 185 L 145 175 L 145 160 Z" },
    { name: "Matale", path: "M 185 145 L 205 135 L 230 165 L 228 185 L 210 195 L 195 188 L 188 175 Z" },
    { name: "Batticaloa", path: "M 248 158 L 268 165 L 272 185 L 268 205 L 258 215 L 240 208 L 230 190 L 230 165 Z" },
    { name: "Ampara", path: "M 240 208 L 258 215 L 265 235 L 260 255 L 242 258 L 228 248 L 225 225 Z" },
    { name: "Kandy", path: "M 188 185 L 195 188 L 210 195 L 218 210 L 210 222 L 195 220 L 182 210 L 178 195 Z" },
    { name: "Nuwara Eliya", path: "M 195 220 L 210 222 L 220 235 L 218 248 L 205 252 L 190 245 L 188 230 Z" },
    { name: "Badulla", path: "M 218 210 L 230 190 L 240 208 L 242 230 L 235 248 L 220 250 L 210 235 Z" },
    { name: "Monaragala", path: "M 225 225 L 242 230 L 260 255 L 258 275 L 245 285 L 228 280 L 218 265 L 220 248 Z" },
    { name: "Kegalle", path: "M 155 185 L 170 190 L 182 210 L 178 225 L 165 232 L 152 225 L 148 205 Z" },
    { name: "Ratnapura", path: "M 165 232 L 178 225 L 190 245 L 188 265 L 175 275 L 160 270 L 152 255 L 155 240 Z" },
    { name: "Colombo", path: "M 145 195 L 155 195 L 165 205 L 165 220 L 158 228 L 145 225 L 138 212 Z" },
    { name: "Gampaha", path: "M 145 175 L 160 178 L 170 190 L 168 205 L 155 210 L 145 205 L 140 188 Z" },
    { name: "Kalutara", path: "M 145 225 L 158 228 L 165 242 L 162 258 L 150 262 L 140 252 L 138 235 Z" },
    { name: "Galle", path: "M 150 262 L 162 258 L 175 275 L 178 290 L 168 298 L 152 292 L 145 278 Z" },
    { name: "Matara", path: "M 168 298 L 178 290 L 195 295 L 205 305 L 202 318 L 188 320 L 175 312 Z" },
    { name: "Hambantota", path: "M 188 265 L 205 252 L 228 280 L 235 298 L 230 312 L 215 315 L 202 310 L 195 295 Z" },
  ];

  return (
    <div className="relative w-full aspect-[4/5] bg-muted/20 rounded border border-border tactical-grid">
      <svg viewBox="0 0 300 350" className="w-full h-full">
        {districts.map((district) => {
          const isSelected = selectedDistrict === district.name;
          const alertCount = alertCounts[district.name] || 0;
          const hasAlerts = alertCount > 0;
          
          // Calculate center point for alert badge
          const pathPoints = district.path.match(/\d+/g)?.map(Number) || [];
          const xCoords = pathPoints.filter((_, i) => i % 2 === 0);
          const yCoords = pathPoints.filter((_, i) => i % 2 === 1);
          const centerX = xCoords.reduce((a, b) => a + b, 0) / xCoords.length;
          const centerY = yCoords.reduce((a, b) => a + b, 0) / yCoords.length;
          
          return (
            <g key={district.name}>
              <motion.path
                d={district.path}
                fill={
                  isSelected 
                    ? "hsl(var(--primary))" 
                    : hasAlerts 
                      ? "hsl(var(--destructive) / 0.3)" 
                      : "hsl(var(--muted) / 0.5)"
                }
                stroke={
                  isSelected 
                    ? "hsl(var(--primary))" 
                    : hasAlerts 
                      ? "hsl(var(--destructive))" 
                      : "hsl(var(--border))"
                }
                strokeWidth={isSelected ? "3" : hasAlerts ? "2" : "1"}
                className="cursor-pointer transition-all"
                onClick={() => onDistrictSelect(district.name)}
                whileHover={{ 
                  fill: "hsl(var(--primary) / 0.6)",
                  strokeWidth: 2.5
                }}
                whileTap={{ scale: 0.98 }}
                animate={hasAlerts ? { 
                  opacity: [1, 0.7, 1],
                } : {}}
                transition={hasAlerts ? { 
                  duration: 2, 
                  repeat: Infinity,
                  ease: "easeInOut"
                } : {
                  duration: 0.2
                }}
              />
              {/* Alert badge */}
              {hasAlerts && (
                <motion.g
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200 }}
                >
                  <circle
                    cx={centerX}
                    cy={centerY}
                    r="10"
                    fill="hsl(var(--destructive))"
                    stroke="hsl(var(--background))"
                    strokeWidth="2"
                  />
                  <text
                    x={centerX}
                    y={centerY + 4}
                    textAnchor="middle"
                    className="text-[12px] font-bold fill-destructive-foreground pointer-events-none"
                    style={{ userSelect: 'none' }}
                  >
                    {alertCount}
                  </text>
                </motion.g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-card/90 border border-border rounded p-3 space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-muted/50"></div>
          <span className="text-xs font-mono">No Alerts</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-destructive animate-pulse"></div>
          <span className="text-xs font-mono">Active Alerts</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-primary"></div>
          <span className="text-xs font-mono">Selected</span>
        </div>
      </div>

      {/* Alert Summary */}
      <div className="absolute top-4 right-4 bg-card/90 border border-border rounded p-3">
        <div className="text-center">
          <p className="text-2xl font-bold text-destructive">
            {Object.values(alertCounts).reduce((a, b) => a + b, 0)}
          </p>
          <p className="text-xs text-muted-foreground uppercase">Total Alerts</p>
        </div>
      </div>
    </div>
  );
};

export default SriLankaMap;