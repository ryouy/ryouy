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

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="236" viewBox="0 0 560 236" role="img" aria-label="Azumino weather: {temp}, {condition}">
  <title>Current weather in Azumino, Nagano</title>
  <rect x="1" y="1" width="558" height="234" rx="17" fill="#101b2b" stroke="#2d4158" stroke-width="2"/>
  <text x="26" y="39" fill="#8ac7ee" font-size="18" font-family="Arial,Helvetica,sans-serif" letter-spacing="1.3">AZUMINO / NAGANO</text>
  <text x="25" y="125" fill="#f8fafc" font-size="68" font-family="Arial,Helvetica,sans-serif" font-weight="bold">{temp}</text>
  <text x="27" y="166" fill="#c3d5e5" font-size="20" font-family="Arial,Helvetica,sans-serif">{condition}</text>
  <line x1="289" y1="55" x2="289" y2="180" stroke="#33475c"/>
  <text x="314" y="80" fill="#d5e4ef" font-size="18" font-family="Arial,Helvetica,sans-serif">High {high} / Low {low}</text>
  <text x="314" y="122" fill="#d5e4ef" font-size="18" font-family="Arial,Helvetica,sans-serif">Feels like {feels}</text>
  <text x="314" y="164" fill="#d5e4ef" font-size="18" font-family="Arial,Helvetica,sans-serif">Humidity {humidity}</text>
  <line x1="25" y1="192" x2="535" y2="192" stroke="#33475c"/>
  <text x="27" y="216" fill="#849db2" font-size="14" font-family="Arial,Helvetica,sans-serif">Updated {observed}  ·  Open-Meteo</text>
</svg>'''
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")
print(f"Updated {OUTPUT}: {temp}, {condition} at {observed}")
