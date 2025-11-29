'use client'
import { useState } from "react";
import SriLankaMap from "./SriLankaMap";
import DistrictInfoPanel from "./DistrictInfoPanel";
import { Card } from "../ui/card";
import { MapPin } from "lucide-react";

const MapView = () => {
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <Card className="p-6 bg-card border-border">
        <div className="flex items-center gap-2 mb-4">
          <MapPin className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold">TERRITORY MAP</h2>
          <span className="ml-auto text-xs font-mono text-muted-foreground">
            Click any district for detailed intelligence
          </span>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <SriLankaMap 
              selectedDistrict={selectedDistrict}
              onDistrictSelect={setSelectedDistrict}
            />
          </div>
          
          <div className="lg:col-span-1">
            <DistrictInfoPanel district={selectedDistrict} />
          </div>
        </div>
      </Card>
    </div>
  );
};

export default MapView;
