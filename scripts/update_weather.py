#!/usr/bin/env python3
"""Azumino current weather and tomorrow forecast. Data: https://open-meteo.com/.

The 420:148 canvas ratio matches the profile's aligned layout.
"""
import json
import math
from profile_slices import write_slices, style_card, light_card
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

LATITUDE, LONGITUDE = 36.3044, 137.9061
OUTPUT = Path(__file__).resolve().parents[1] / 'assets/weather-azumino.svg'
WEATHER_NAMES = {0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 56: 'Freezing drizzle', 57: 'Freezing drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Light showers', 81: 'Rain showers', 82: 'Heavy showers', 85: 'Snow showers', 86: 'Snow showers', 95: 'Thunderstorm', 96: 'Thunder + hail', 99: 'Thunder + hail'}


def format_temperature(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return f"{value:.0f}°"
    return '—'


def render_card(payload: dict) -> str:
    current, daily = payload['current'], payload.get('daily') or {}
    observed = datetime.fromisoformat(current['time'])
    tomorrow = observed.date() + timedelta(days=1)
    dates = daily.get('time') or []
    def forecast(field, day):
        values = daily.get(field) or []
        if day.isoformat() not in dates:
            return None
        index = dates.index(day.isoformat())
        return values[index] if index < len(values) else None
    temperature = format_temperature(current.get('temperature_2m'))
    high = format_temperature(forecast('temperature_2m_max', tomorrow))
    low = format_temperature(forecast('temperature_2m_min', tomorrow))
    today_high = format_temperature(forecast('temperature_2m_max', observed.date()))
    today_low = format_temperature(forecast('temperature_2m_min', observed.date()))
    now_name = WEATHER_NAMES.get(current.get('weather_code'), 'Unavailable')
    tomorrow_name = WEATHER_NAMES.get(forecast('weather_code', tomorrow), 'Unavailable')
    description = escape(f'Azumino: now {temperature}C, {now_name}. Today high {today_high}, low {today_low}. Tomorrow {tomorrow.month}/{tomorrow.day}: {tomorrow_name}, high {high}, low {low}.')
    return style_card(f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="148" viewBox="0 0 420 148" role="img" aria-label="{description}">
  <title>{description}</title>
  <rect x="1" y="1" width="418" height="146" rx="13" fill="#101b2b" stroke="#2a3e54" stroke-width="1.5"/>
  <g font-family="Arial,Helvetica,sans-serif">
    <text x="20" y="28" fill="#8abfe5" font-size="15" font-weight="600" letter-spacing="1.2">AZUMINO</text>
    <text x="400" y="28" text-anchor="end" fill="#879fb2" font-size="11">{observed:%m/%d %H:%M}</text>
    <text x="81.5" y="88" text-anchor="middle" dominant-baseline="central" fill="#f7fbff" font-size="57" font-weight="600">{temperature.removesuffix('°')}<tspan font-size="30">°C</tspan></text>
    <line x1="163" y1="45" x2="163" y2="131" stroke="#314558"/>
    <text x="180" y="58" fill="#f7fbff" font-size="17">{now_name}</text>
    <text x="180" y="83" fill="#d2e1ed" font-size="15">High {today_high} / Low {today_low}</text>
    <text x="180" y="110" fill="#879fb2" font-size="12">Tomorrow</text>
    <text x="248" y="110" fill="#d2e1ed" font-size="14">{tomorrow_name}</text>
    <text x="180" y="132" fill="#b6cadb" font-size="15">High {high} / Low {low}</text>
  </g>
</svg>
''')



def animated_sky(light=False):
    """Generate a compact original animated GIF, embedded directly in the SVG.

    Self-contained image data matters because GitHub's SVG image proxy may block
    externally referenced pictures. Both theme versions keep their own palette.
    """
    import base64
    import io
    from PIL import Image, ImageDraw, ImageFilter

    w, h = 420, 148
    frames = []
    for frame in range(20):
        image = Image.new('RGB', (w, h))
        pixels = image.load()
        for y in range(h):
            t = y / max(1, h - 1)
            if light:
                top, bottom = (205, 225, 240), (240, 245, 249)
            else:
                top, bottom = (14, 32, 57), (37, 69, 91)
            color = tuple(round(a * (1 - t) + b * t) for a, b in zip(top, bottom))
            for px in range(w):
                pixels[px, y] = color

        # Muted drifting cloud bands and a mountain profile evoke Azumino.
        overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        offset = (frame * 3) % 100
        cloud = (255, 255, 255, 42 if light else 22)
        for origin, cy, scale in [(-105, 38, 1), (145, 81, 2), (280, 19, 1)]:
            cx = origin + offset
            for dx, dy, r in [(-29, 2, 23), (0, -6, 33), (34, 3, 24)]:
                rr = r * scale // 2
                draw.ellipse((cx + dx - rr, cy + dy - rr // 2,
                              cx + dx + rr, cy + dy + rr // 2), fill=cloud)
        overlay = overlay.filter(ImageFilter.GaussianBlur(8))
        image = Image.alpha_composite(image.convert('RGBA'), overlay)
        mountain = ImageDraw.Draw(image)
        ridge = [(0, 132), (28, 117), (45, 122), (87, 92), (112, 108),
                 (147, 83), (172, 99), (214, 71), (243, 91), (278, 61),
                 (315, 103), (347, 82), (379, 111), (420, 91), (420, 148), (0, 148)]
        mountain.polygon(ridge, fill=(133, 163, 177, 90) if light else (72, 107, 128, 90))
        mountain.polygon([(0, 143), (48, 128), (112, 136), (178, 115),
                          (232, 138), (298, 112), (350, 130), (420, 118),
                          (420, 148), (0, 148)],
                         fill=(157, 180, 186, 75) if light else (36, 74, 93, 140))
        frames.append(image.convert('RGB').quantize(colors=48))
    buffer = io.BytesIO()
    frames[0].save(buffer, format='GIF', save_all=True, append_images=frames[1:],
                   duration=150, loop=0, optimize=True, disposal=2)
    return 'data:image/gif;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def add_background(svg, gif_uri, light=False):
    """Place the moving scenery behind weather content, inside rounded edges."""
    import xml.etree.ElementTree as ET
    ns = '{http://www.w3.org/2000/svg}'
    root = ET.fromstring(svg)
    defs = root.find(ns + 'defs')
    if defs is None:
        defs = ET.Element(ns + 'defs')
        root.insert(0, defs)
    clip = ET.SubElement(defs, ns + 'clipPath', {'id': 'weather-sky-clip'})
    ET.SubElement(clip, ns + 'rect', {'x':'1','y':'1','width':'418','height':'146','rx':'13'})
    # Background rect and decorative ridge remain underneath the animated sky.
    background = ET.Element(ns + 'image', {
        'x':'1', 'y':'1', 'width':'418', 'height':'146',
        'preserveAspectRatio':'xMidYMid slice',
        'clip-path':'url(#weather-sky-clip)', 'href':gif_uri,
        'aria-hidden':'true'})
    surface = next(el for el in root if el.tag == ns + 'rect' and
                   el.get('fill') == 'url(#profile-card-surface)')
    root.insert(list(root).index(surface) + 1, background)
    # Preserve enough contrast over the sky in both themes.
    fade = ET.Element(ns + 'rect', {'x':'1','y':'1','width':'418','height':'146',
        'rx':'13', 'fill':'#ffffff' if light else '#071421',
        'opacity':'.28' if light else '.32', 'aria-hidden':'true'})
    root.insert(list(root).index(background) + 1, fade)
    return ET.tostring(root, encoding='unicode') + '\\n'


def main() -> None:
    query = (
        'https://api.open-meteo.com/v1/forecast'
        f'?latitude={LATITUDE}&longitude={LONGITUDE}'
        '&current=temperature_2m,weather_code,is_day'
        '&daily=weather_code,temperature_2m_max,temperature_2m_min'
        '&timezone=Asia%2FTokyo&forecast_days=2'
    )
    request = Request(query, headers={'User-Agent': 'ryouy-github-readme-weather/2.0'})
    import time
    payload = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=18) as response:
                payload = json.load(response)
            break
        except Exception as exc:
            print(f'Weather fetch attempt {attempt + 1}/3 failed: {exc}')
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    light_output = OUTPUT.with_name('weather-azumino-light.svg')
    if payload is not None:
        dark_source = render_card(payload)
        light_source = light_card(dark_source)
    elif OUTPUT.exists() and light_output.exists():
        # Keep the last valid observed conditions during temporary API outages.
        dark_source = OUTPUT.read_text(encoding='utf-8')
        light_source = light_output.read_text(encoding='utf-8')
        print('Using last successfully generated weather data')
    else:
        raise RuntimeError('Weather service unavailable and no cached cards exist')
    svg = dark_source if 'weather-sky-clip' in dark_source else add_background(dark_source, animated_sky(light=False))
    OUTPUT.write_text(svg, encoding='utf-8')
    write_slices(svg, OUTPUT)
    light_svg = light_source if 'weather-sky-clip' in light_source else add_background(light_source, animated_sky(light=True), light=True)
    light_output.write_text(light_svg, encoding='utf-8')
    write_slices(light_svg, light_output)
    print(f'Updated both themes for {OUTPUT.name}: current conditions and tomorrow forecast')


if __name__ == '__main__':
    main()


