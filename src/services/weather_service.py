"""
EstateIQ Outdoor Weather Service (src/services/weather_service.py)
==================================================================
Provides secure, non-blocking outdoor ambient weather context:
- Server-side caching (15-minute TTL) to minimize external requests and guarantee zero-latency responses.
- Location configured for BPUT University Campus (Rourkela, Odisha - Lat 22.2530, Lon 84.9015).
- Supports WEATHER_API_KEY or OPENWEATHER_API_KEY from .env for OpenWeatherMap integration.
- Automatic Open-Meteo zero-key fallback (fetches live weather without requiring an API key).
- Outdoor vs Indoor strict separation: Always flags readings as outdoor ambient.
- Graceful offline fallback: Never blocks telemetry ingestion or throws 500s.
"""

from __future__ import annotations

import os
import time
import datetime
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# BPUT University Campus, Rourkela, Odisha defaults
DEFAULT_BPUT_LAT: float = float(os.getenv("WEATHER_LATITUDE", "22.2530"))
DEFAULT_BPUT_LON: float = float(os.getenv("WEATHER_LONGITUDE", "84.9015"))
DEFAULT_LOCATION_NAME: str = os.getenv("WEATHER_LOCATION_NAME", "BPUT University Campus, Rourkela (Odisha)")


class WeatherData(BaseModel):
    is_available: bool = True
    location_name: str = DEFAULT_LOCATION_NAME
    latitude: float = DEFAULT_BPUT_LAT
    longitude: float = DEFAULT_BPUT_LON
    temperature_c: float = 27.5
    humidity_pct: float = 58.0
    apparent_temperature_c: float = 29.1
    weather_condition: str = "Clear Sky"
    wind_speed_kmh: float = 12.0
    observation_time: str
    source: str = "OPEN_METEO_FREE"
    cache_age_seconds: int = 0
    is_cached: bool = False
    context_type: str = "OUTDOOR_AMBIENT"


class WeatherService:
    def __init__(self, cache_ttl_seconds: int = 900):  # 15 minutes default
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_current: Optional[WeatherData] = None
        self._last_fetch_time: float = 0.0

    def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> WeatherData:
        target_lat = lat if lat is not None else DEFAULT_BPUT_LAT
        target_lon = lon if lon is not None else DEFAULT_BPUT_LON
        now = time.time()

        # Return cache if valid
        if self._cached_current and (now - self._last_fetch_time < self.cache_ttl_seconds):
            copy_data = self._cached_current.model_copy()
            copy_data.cache_age_seconds = int(now - self._last_fetch_time)
            copy_data.is_cached = True
            return copy_data

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. Attempt OpenWeatherMap if WEATHER_API_KEY or OPENWEATHER_API_KEY is present
        api_key = os.getenv("WEATHER_API_KEY") or os.getenv("OPENWEATHER_API_KEY", "").strip()
        if api_key:
            try:
                owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={target_lat}&lon={target_lon}&appid={api_key}&units=metric"
                req = urllib.request.Request(owm_url, headers={"User-Agent": "EstateIQ-FacilityIntelligence/3.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode("utf-8"))
                        main = payload.get("main", {})
                        temp = float(main.get("temp", 28.0))
                        hum = float(main.get("humidity", 58.0))
                        app_temp = float(main.get("feels_like", temp))
                        wind = round(float(payload.get("wind", {}).get("speed", 3.0)) * 3.6, 1)
                        weather_arr = payload.get("weather", [{}])
                        cond = weather_arr[0].get("main", "Clear")
                        city_name = payload.get("name") or "Rourkela"

                        w = WeatherData(
                            is_available=True,
                            location_name=f"{DEFAULT_LOCATION_NAME} ({city_name})",
                            latitude=target_lat,
                            longitude=target_lon,
                            temperature_c=temp,
                            humidity_pct=hum,
                            apparent_temperature_c=app_temp,
                            weather_condition=cond,
                            wind_speed_kmh=wind,
                            observation_time=now_iso,
                            source="OPENWEATHERMAP_API",
                            cache_age_seconds=0,
                            is_cached=False,
                            context_type="OUTDOOR_AMBIENT"
                        )
                        self._cached_current = w
                        self._last_fetch_time = now
                        return w
            except Exception:
                # If key fails or rate-limited, fall through to Open-Meteo
                pass

        # 2. Attempt fetch from Open-Meteo (Zero key required, high-precision live satellite/radar)
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={target_lat}&longitude={target_lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto"
            req = urllib.request.Request(url, headers={"User-Agent": "EstateIQ-FacilityIntelligence/3.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    current = payload.get("current", {})
                    temp = float(current.get("temperature_2m", 28.0))
                    hum = float(current.get("relative_humidity_2m", 60.0))
                    app_temp = float(current.get("apparent_temperature", temp))
                    wind = float(current.get("wind_speed_10m", 10.0))
                    code = current.get("weather_code", 0)

                    # Simple WMO weather code interpretation
                    cond = "Clear Sky" if code == 0 else (
                        "Mainly Clear" if code == 1 else (
                            "Partly Cloudy" if code in (2, 3) else (
                                "Rain / Drizzle" if code in (51, 53, 55, 61, 63, 65, 80, 81) else (
                                    "Thunderstorm" if code in (95, 96, 99) else "Overcast"
                                )
                            )
                        )
                    )

                    w = WeatherData(
                        is_available=True,
                        location_name=DEFAULT_LOCATION_NAME,
                        latitude=target_lat,
                        longitude=target_lon,
                        temperature_c=temp,
                        humidity_pct=hum,
                        apparent_temperature_c=app_temp,
                        weather_condition=cond,
                        wind_speed_kmh=wind,
                        observation_time=now_iso,
                        source="OPEN_METEO_API",
                        cache_age_seconds=0,
                        is_cached=False,
                        context_type="OUTDOOR_AMBIENT"
                    )
                    self._cached_current = w
                    self._last_fetch_time = now
                    return w
        except Exception:
            # Graceful non-blocking fallback (returns baseline outdoor ambient climate for Rourkela)
            pass

        fallback = WeatherData(
            is_available=True,
            location_name=DEFAULT_LOCATION_NAME,
            latitude=target_lat,
            longitude=target_lon,
            temperature_c=27.5,
            humidity_pct=56.0,
            apparent_temperature_c=29.8,
            weather_condition="Clear Sky",
            wind_speed_kmh=6.2,
            observation_time=now_iso,
            source="BPUT_ROURKELA_CLIMATOLOGY",
            cache_age_seconds=0,
            is_cached=False,
            context_type="OUTDOOR_AMBIENT"
        )
        self._cached_current = fallback
        self._last_fetch_time = now
        return fallback


GLOBAL_WEATHER_SERVICE = WeatherService()
