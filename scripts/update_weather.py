#!/usr/bin/env python3
"""Azumino current weather and tomorrow forecast. Data: https://open-meteo.com/.

The 420:148 canvas ratio matches the profile's aligned layout.
"""
import json
from profile_slices import write_slices
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

LATITUDE, LONGITUDE = 36.3044, 137.9061
OUTPUT = Path(__file__).resolve().parents[1] / 'assets/weather-azumino.svg'
WEATHER_NAMES = {0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 56: 'Freezing drizzle', 57: 'Freezing drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Light showers', 81: 'Rain showers', 82: 'Heavy showers', 85: 'Snow showers', 86: 'Snow showers', 95: 'Thunderstorm', 96: 'Thunder + hail', 99: 'Thunder + hail'}


def render_card(payload: dict) -> str:
    current, daily = payload['current'], payload['daily']
    observed = datetime.fromisoformat(current['time'])
    tomorrow = observed.date() + timedelta(days=1)
    today_index = daily['time'].index(observed.date().isoformat())
    index = daily['time'].index(tomorrow.isoformat())
    now_code = int(current['weather_code'])
    tomorrow_code = int(daily['weather_code'][index])
    temperature = f"{current['temperature_2m']:.0f}°"
    high = f"{daily['temperature_2m_max'][index]:.0f}°"
    low = f"{daily['temperature_2m_min'][index]:.0f}°"
    today_high = f"{daily['temperature_2m_max'][today_index]:.0f}°"
    today_low = f"{daily['temperature_2m_min'][today_index]:.0f}°"
    now_name = WEATHER_NAMES.get(now_code, 'Unknown')
    tomorrow_name = WEATHER_NAMES.get(tomorrow_code, 'Unavailable')
    description = escape(f'Azumino: now {temperature}C, {now_name}. Today high {today_high}, low {today_low}. Tomorrow {tomorrow.month}/{tomorrow.day}: {tomorrow_name}, high {high}, low {low}.')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="148" viewBox="0 0 420 148" role="img" aria-label="{description}">
  <title>{description}</title>
  <rect x="1" y="1" width="418" height="146" rx="13" fill="#101b2b" stroke="#2a3e54" stroke-width="1.5"/>
  <g font-family="Arial,Helvetica,sans-serif">
    <text x="20" y="28" fill="#8abfe5" font-size="15" font-weight="600" letter-spacing="1.2">AZUMINO</text>
    <text x="400" y="28" text-anchor="end" fill="#879fb2" font-size="11">{observed:%m/%d %H:%M}</text>
    <text x="18" y="101" fill="#f7fbff" font-size="57" font-weight="600">{temperature[:-1]}<tspan font-size="30">°C</tspan></text>
    <line x1="163" y1="45" x2="163" y2="131" stroke="#314558"/>
    <text x="180" y="58" fill="#f7fbff" font-size="17">{now_name}</text>
    <text x="180" y="83" fill="#d2e1ed" font-size="15">High {today_high} / Low {today_low}</text>
    <text x="180" y="110" fill="#879fb2" font-size="12">Tomorrow</text>
    <text x="248" y="110" fill="#d2e1ed" font-size="14">{tomorrow_name}</text>
    <text x="180" y="132" fill="#b6cadb" font-size="15">High {high} / Low {low}</text>
  </g>
</svg>
'''



def main() -> None:
    query = (
        'https://api.open-meteo.com/v1/forecast'
        f'?latitude={LATITUDE}&longitude={LONGITUDE}'
        '&current=temperature_2m,weather_code,is_day'
        '&daily=weather_code,temperature_2m_max,temperature_2m_min'
        '&timezone=Asia%2FTokyo&forecast_days=2'
    )
    request = Request(query, headers={'User-Agent': 'ryouy-github-readme-weather/2.0'})
    with urlopen(request, timeout=25) as response:
        payload = json.load(response)
    svg = render_card(payload)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding='utf-8')
    write_slices(svg, OUTPUT)
    print(f'Updated {OUTPUT.name}: current conditions and tomorrow forecast')


if __name__ == '__main__':
    main()
