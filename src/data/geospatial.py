"""
Geospatial Facility Intelligence Repository & Folium Map Generator.
Implements spatial data model, GeoPandas integration, campus interactive map,
and OpenStreetMap / Folium rendering with graceful offline fallback.
"""

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, Any, List, Optional

try:
    import folium
    from folium.plugins import MarkerCluster
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False


class GeospatialFacilityRepository:
    """Geospatial database & map builder for EstateIQ campus assets."""
    
    # Representative coordinates for EstateIQ Indian Campus (Main Campus, Bengaluru)
    CAMPUS_CENTER = [12.9716, 77.5946]
    
    DEFAULT_FACILITY_LOCATIONS = [
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_ADMIN_01",
            "name": "Main Administration Block",
            "latitude": 12.9720,
            "longitude": 77.5950,
            "asset_type": "Energy",
            "status": "OPTIMAL",
            "severity": "LOW",
            "metric_value": "78.4 kWh",
            "timestamp": "2026-10-06 06:30:00"
        },
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_HOSTEL_B",
            "name": "Block B Hostel",
            "latitude": 12.9710,
            "longitude": 77.5940,
            "asset_type": "Energy",
            "status": "SURGE_ANOMALY",
            "severity": "HIGH",
            "metric_value": "145.2 kWh (+86%)",
            "timestamp": "2026-10-06 06:30:00"
        },
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_CAFETERIA",
            "name": "Central Cafeteria",
            "latitude": 12.9725,
            "longitude": 77.5935,
            "asset_type": "Waste",
            "status": "OVERFLOW_RISK",
            "severity": "HIGH",
            "metric_value": "92% Capacity",
            "timestamp": "2026-10-06 06:30:00"
        },
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_SUBSTATION",
            "name": "Main Transformer Substation",
            "latitude": 12.9705,
            "longitude": 77.5955,
            "asset_type": "Assets",
            "status": "OPTIMAL",
            "severity": "LOW",
            "metric_value": "415 V • 98.4% Efficiency",
            "timestamp": "2026-10-06 06:30:00"
        },
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_PARKING_A",
            "name": "North Parking Structure",
            "latitude": 12.9730,
            "longitude": 77.5960,
            "asset_type": "Parking",
            "status": "MODERATE",
            "severity": "MEDIUM",
            "metric_value": "142 / 200 Slots Occupied",
            "timestamp": "2026-10-06 06:30:00"
        },
        {
            "facility_id": "FAC_MAIN_01",
            "building_id": "BLD_WATER_PLANT",
            "name": "Water Recycling & STP Unit",
            "latitude": 12.9700,
            "longitude": 77.5930,
            "asset_type": "Water",
            "status": "OPTIMAL",
            "severity": "LOW",
            "metric_value": "42.5 kL Normal Flow",
            "timestamp": "2026-10-06 06:30:00"
        }
    ]

    def __init__(self, locations: Optional[List[Dict[str, Any]]] = None):
        self.raw_data = locations if locations else self.DEFAULT_FACILITY_LOCATIONS
        self.df = pd.DataFrame(self.raw_data)
        
        # Convert to GeoPandas GeoDataFrame
        geometry = [Point(xy) for xy in zip(self.df["longitude"], self.df["latitude"])]
        self.gdf = gpd.GeoDataFrame(self.df, geometry=geometry, crs="EPSG:4326")

    def filter_locations(self, asset_type: Optional[str] = None, severity: Optional[str] = None) -> gpd.GeoDataFrame:
        """Filters spatial locations by asset domain or severity level."""
        filtered = self.gdf.copy()
        if asset_type and asset_type != "All":
            filtered = filtered[filtered["asset_type"] == asset_type]
        if severity and severity != "All":
            filtered = filtered[filtered["severity"] == severity]
        return filtered

    def generate_folium_map(self, asset_type: str = "All", zoom_start: int = 17) -> str:
        """Generates interactive Folium map HTML representation."""
        if not FOLIUM_AVAILABLE:
            return "<div class='map-unavailable-box'><strong>MAP_UNAVAILABLE</strong>: Folium map renderer not installed.</div>"
        
        gdf_subset = self.filter_locations(asset_type=asset_type)
        
        m = folium.Map(
            location=self.CAMPUS_CENTER,
            zoom_start=zoom_start,
            tiles="OpenStreetMap"
        )
        
        marker_cluster = MarkerCluster().add_to(m)

        for _, row in gdf_subset.iterrows():
            status = row["status"]
            icon_color = "red" if status in ["SURGE_ANOMALY", "OVERFLOW_RISK", "CRITICAL"] else ("orange" if status == "MODERATE" else "green")
            
            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px; width: 200px;">
                <h4 style="margin: 0 0 6px 0; color: #124B3E;">{row['name']}</h4>
                <b>Asset Type:</b> {row['asset_type']}<br/>
                <b>Status:</b> <span style="color: {'#DC2626' if icon_color=='red' else '#124B3E'}; font-weight: bold;">{row['status']}</span><br/>
                <b>Telemetry:</b> {row['metric_value']}<br/>
                <small style="color: #64748B;">{row['timestamp']}</small>
            </div>
            """
            
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['name']} ({row['status']})",
                icon=folium.Icon(color=icon_color, icon="info-sign")
            ).add_to(marker_cluster)

        return m._repr_html_()
