#!/usr/bin/env python3
"""Azumino current weather and tomorrow forecast. Data: https://open-meteo.com/.

The 420:148 canvas ratio matches the profile's aligned layout.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

LATITUDE, LONGITUDE = 36.3044, 137.9061
OUTPUT = Path(__file__).resolve().parents[1] / 'assets/weather-azumino.svg'
WEATHER_NAMES = {
    0: '晴れ', 1: 'ほぼ晴れ', 2: '晴れ時々くもり', 3: 'くもり',
    45: '霧', 48: '霧', 51: '霧雨', 53: '霧雨', 55: '強い霧雨',
    56: '凍る霧雨', 57: '凍る霧雨', 61: '小雨', 63: '雨', 65: '強い雨',
    66: '凍る雨', 67: '凍る雨', 71: '小雪', 73: '雪', 75: '強い雪',
    77: '雪', 80: 'にわか雨', 81: 'にわか雨', 82: '強いにわか雨',
    85: 'にわか雪', 86: '強いにわか雪', 95: '雷雨', 96: '雷雨・ひょう',
    99: '雷雨・ひょう',
}


def weather_icon(code: int, x: int, y: int, night: bool = False) -> str:
    sun = '<circle cx="16" cy="16" r="7"/><path d="M16 2v3m0 22v3M2 16h3m22 0h3M6 6l2 2m16 16 2 2M6 26l2-2M24 8l2-2"/>'
    moon = '<path d="M25 21A12 12 0 0 1 11 5a12 12 0 1 0 14 16Z"/>'
    cloud = '<path d="M8 23h17a6 6 0 0 0 0-12 9 9 0 0 0-17-1 6.5 6.5 0 0 0 0 13Z"/>'
    if code in (0, 1):
        drawing = moon if night else sun
    elif code == 2:
        drawing = '<g transform="translate(0 -1) scale(.68)">' + (moon if night else sun) + '</g>' + cloud
    elif code == 3:
        drawing = cloud
    elif code in (45, 48):
        drawing = '<path d="M5 9h22M2 16h28M5 23h22"/>'
    elif code in (71, 73, 75, 77, 85, 86):
        drawing = cloud + '<path d="M10 26v6m-3-3h6m8-3v6m-3-3h6"/>'
    elif code in (95, 96, 99):
        drawing = cloud + '<path d="m17 22-4 6h5l-3 6"/>'
    elif code in WEATHER_NAMES:
        drawing = cloud + '<path d="m10 27-2 4m10-4-2 4m10-4-2 4"/>'
    else:
        drawing = cloud
    return f'<g transform="translate({x} {y})" fill="none" stroke="#8abfe5" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{drawing}</g>'


def render_card(payload: dict) -> str:
    current, daily = payload['current'], payload['daily']
    observed = datetime.fromisoformat(current['time'])
    tomorrow = observed.date() + timedelta(days=1)
    index = daily['time'].index(tomorrow.isoformat())
    now_code = int(current['weather_code'])
    tomorrow_code = int(daily['weather_code'][index])
    temperature = f"{current['temperature_2m']:.0f}°"
    high = f"{daily['temperature_2m_max'][index]:.0f}°"
    low = f"{daily['temperature_2m_min'][index]:.0f}°"
    now_name = WEATHER_NAMES.get(now_code, '天気不明')
    tomorrow_name = WEATHER_NAMES.get(tomorrow_code, '予報なし')
    description = escape(f'安曇野：現在 {temperature}C、{now_name}。明日 {tomorrow.month}/{tomorrow.day} {tomorrow_name}、最高 {high}、最低 {low}。')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="148" viewBox="0 0 420 148" role="img" aria-label="{description}">
  <title>{description}</title>
  <rect x="1" y="1" width="418" height="146" rx="13" fill="#101b2b" stroke="#2a3e54" stroke-width="1.5"/>
  <g font-family="Arial,'Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif">
    <text x="20" y="28" fill="#8abfe5" font-size="15" font-weight="600" letter-spacing="1.2">AZUMINO</text>
    <text x="400" y="28" text-anchor="end" fill="#879fb2" font-size="11">{observed:%m/%d %H:%M}</text>
    <line x1="199" y1="45" x2="199" y2="128" stroke="#314558"/>
    <text x="20" y="53" fill="#879fb2" font-size="11">現在</text>
    <text x="18" y="102" fill="#f7fbff" font-size="52" font-weight="600">{temperature[:-1]}<tspan font-size="23">°C</tspan></text>
    <text x="20" y="127" fill="#d2e1ed" font-size="14">{now_name}</text>
    <text x="220" y="53" fill="#879fb2" font-size="11">明日 {tomorrow.month}/{tomorrow.day}</text>
    <text x="260" y="87" fill="#f7fbff" font-size="16">{tomorrow_name}</text>
    <text x="220" y="124" fill="#d2e1ed" font-size="16">最高 {high}  /  最低 {low}</text>
  </g>
  {weather_icon(now_code, 145, 68, not bool(current['is_day']))}
  {weather_icon(tomorrow_code, 219, 64)}
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
    print(f'Updated {OUTPUT.name}: current conditions and tomorrow forecast')


if __name__ == '__main__':
    main()
