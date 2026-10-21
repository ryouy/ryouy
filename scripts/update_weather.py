#!/usr/bin/env python3
"""Build a self-hosted GitHub README weather card for Azumino, Nagano."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

LATITUDE = 36.3044  # Azumino City Hall (official city coordinates)
LONGITUDE = 137.9061
OUTPUT = Path("assets/weather-azumino.svg")

WEATHER_NAMES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm",
}

query = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code"
    "&daily=temperature_2m_max,temperature_2m_min"
    "&timezone=Asia%2FTokyo&forecast_days=1"
)
request = Request(query, headers={"User-Agent": "ryouy-github-readme-weather/1.0"})
with urlopen(request, timeout=25) as response:
    payload = json.load(response)

current = payload["current"]
daily = payload["daily"]
temp = f'{current["temperature_2m"]:.0f}°C'
feels = f'{current["apparent_temperature"]:.0f}°C'
humidity = f'{current["relative_humidity_2m"]:.0f}%'
high = f'{daily["temperature_2m_max"][0]:.0f}°'
low = f'{daily["temperature_2m_min"][0]:.0f}°'
condition = escape(WEATHER_NAMES.get(int(current["weather_code"]), "Current weather"))
observed = escape(current["time"].replace("T", " ") + " JST")

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="148" viewBox="0 0 420 148" role="img" aria-label="Azumino weather: {temp}, {condition}">
  <title>Current weather in Azumino, Nagano</title>
  <rect x="1" y="1" width="418" height="146" rx="13" fill="#101b2b" stroke="#2a3e54" stroke-width="1.5"/>
  <text x="20" y="28" fill="#8abfe5" font-size="15" font-weight="600" font-family="Arial,Helvetica,sans-serif" letter-spacing="1.2">AZUMINO</text>
  <text x="400" y="28" text-anchor="end" fill="#8097ad" font-size="11" font-family="Arial,Helvetica,sans-serif" letter-spacing="1.0">WEATHER</text>
  <text x="18" y="99" fill="#f7fbff" font-size="57" font-weight="600" font-family="Arial,Helvetica,sans-serif">{temp}</text>
  <line x1="163" y1="43" x2="163" y2="111" stroke="#314558" stroke-width="1"/>
  <text x="180" y="57" fill="#f7fbff" font-size="17" font-family="Arial,Helvetica,sans-serif">{condition}</text>
  <text x="180" y="85" fill="#d2e1ed" font-size="16" font-family="Arial,Helvetica,sans-serif">High {high}  /  Low {low}</text>
  <text x="180" y="108" fill="#b6cadb" font-size="13" font-family="Arial,Helvetica,sans-serif">Feels {feels}  ·  Humidity {humidity}</text>
  <text x="20" y="132" fill="#879fb2" font-size="11" font-family="Arial,Helvetica,sans-serif">{observed} JST · Open-Meteo</text>
</svg>'''
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")
print(f"Updated {OUTPUT}: {temp}, {condition} at {observed}")
