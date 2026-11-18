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
PANORAMA = OUTPUT.parent / 'azumino_alps_weather_background.gif'
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


def weather_background(light=False):
    """Prefer the user's custom Azumino panorama GIF when installed."""
    import base64
    if PANORAMA.is_file():
        raw = PANORAMA.read_bytes()
        if not raw.startswith((b'GIF87a', b'GIF89a')):
            raise ValueError(f'Invalid GIF: {PANORAMA}')
        return 'data:image/gif;base64,' + base64.b64encode(raw).decode('ascii')
    return animated_sky(light=light)


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
        'opacity':'.68' if light else '.58', 'aria-hidden':'true'})
    root.insert(list(root).index(background) + 1, fade)
    return ET.tostring(root, encoding='unicode') + '\n'



def raster_weather_cards(payload: dict, light: bool = False):
    """Return top and bottom animated GIF bytes for GitHub's image proxy.

    GitHub renders ordinary animated GIFs reliably, unlike GIFs nested inside
    SVG <image> tags. The original panorama is stored in assets/ and composited
    beneath live forecast text on each weather update.
    """
    import io
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFile
    # Tolerate an incomplete GIF trailer in the imported artwork and re-encode
    # every displayed frame as a fresh, valid GIF below.
    ImageFile.LOAD_TRUNCATED_IMAGES = True

    if not PANORAMA.is_file():
        raise FileNotFoundError(f'Weather background is missing: {PANORAMA}')
    source = Image.open(PANORAMA)
    if getattr(source, 'n_frames', 1) < 2:
        raise ValueError('Expected an animated panorama with at least 2 frames')

    current, daily = payload['current'], payload.get('daily') or {}
    observed = datetime.fromisoformat(current['time'])
    next_day = observed.date() + timedelta(days=1)
    dates = daily.get('time') or []
    def forecast(field, day):
        items = daily.get(field) or []
        if day.isoformat() not in dates:
            return None
        i = dates.index(day.isoformat())
        return items[i] if i < len(items) else None

    now = format_temperature(current.get('temperature_2m')).removesuffix('°')
    weather = WEATHER_NAMES.get(current.get('weather_code'), 'Unavailable')
    today_hi = format_temperature(forecast('temperature_2m_max', observed.date()))
    today_lo = format_temperature(forecast('temperature_2m_min', observed.date()))
    tomorrow = WEATHER_NAMES.get(forecast('weather_code', next_day), 'Unavailable')
    next_hi = format_temperature(forecast('temperature_2m_max', next_day))
    next_lo = format_temperature(forecast('temperature_2m_min', next_day))
    palette = {
        'main': '#24292f' if light else '#f7fbff',
        'muted': '#57606a' if light else '#b2c6d5',
        'accent': '#0969da' if light else '#98d4fa',
        'sub': '#424a53' if light else '#d2e1ed',
        'surface': '#ffffff' if light else '#0c1a2b',
        'border': '#d0d7de' if light else '#344b62',
    }
    def font(size, bold=False):
        name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    frames = []
    for i in range(source.n_frames):
        source.seek(i)
        image = ImageOps.fit(source.convert('RGB'), (420, 148),
                             method=Image.Resampling.LANCZOS,
                             centering=(.5, .54)).convert('RGBA')
        wash = Image.new('RGBA', image.size,
                         (255, 255, 255, 202) if light else (6, 20, 33, 176))
        image = Image.alpha_composite(image, wash).convert('RGB')
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((1, 1, 418, 146), radius=13,
                               outline=palette['border'], width=1)
        draw.text((20, 12), 'AZUMINO', font=font(15, True), fill=palette['accent'])
        draw.text((400, 17), observed.strftime('%m/%d %H:%M'),
                  font=font(11), fill=palette['muted'], anchor='ra')
        draw.text((83, 88), now, font=font(51, True),
                  fill=palette['main'], anchor='mm')
        draw.text((129, 89), '°C', font=font(23),
                  fill=palette['main'], anchor='mm')
        draw.line((163, 45, 163, 131), fill=palette['border'], width=1)
        draw.text((180, 44), weather, font=font(16), fill=palette['main'])
        draw.text((180, 70), f'High {today_hi} / Low {today_lo}',
                  font=font(13), fill=palette['sub'])
        draw.text((180, 97), 'Tomorrow', font=font(12), fill=palette['muted'])
        draw.text((248, 96), tomorrow, font=font(12), fill=palette['sub'])
        draw.text((180, 119), f'High {next_hi} / Low {next_lo}',
                  font=font(13), fill=palette['sub'])
        frames.append(image)

    def encode(cropped):
        output = io.BytesIO()
        cropped[0].save(output, format='GIF', save_all=True,
                        append_images=cropped[1:],
                        duration=1400, loop=0, optimize=True, disposal=2)
        return output.getvalue()
    return (encode([im.crop((0, 0, 420, 74)) for im in frames]),
            encode([im.crop((0, 74, 420, 148)) for im in frames]))



def repair_panorama_if_needed() -> None:
    """Normalize a damaged GIF source once, preserving its moving frames."""
    import io
    from PIL import Image, ImageFile

    if not PANORAMA.exists():
        raise FileNotFoundError(f'Missing panorama: {PANORAMA}')
    previous = ImageFile.LOAD_TRUNCATED_IMAGES
    try:
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        try:
            with Image.open(PANORAMA) as original:
                if original.n_frames < 2:
                    raise ValueError('Panorama must be animated')
                for index in range(original.n_frames):
                    original.seek(index)
                    original.convert('RGB').load()
            return
        except OSError:
            # Previously imported binary was missing a few bytes. Re-encode
            # the readable frames into a well-formed standalone GIF.
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            with Image.open(PANORAMA) as damaged:
                frames = []
                for index in range(damaged.n_frames):
                    damaged.seek(index)
                    frames.append(damaged.convert('RGB').copy())
            if len(frames) < 2:
                raise ValueError('Not enough panorama frames to restore')
            buffer = io.BytesIO()
            frames[0].save(buffer, format='GIF', save_all=True,
                           append_images=frames[1:], duration=1400,
                           loop=0, optimize=True, disposal=2)
            replacement = buffer.getvalue()
            ImageFile.LOAD_TRUNCATED_IMAGES = False
            with Image.open(io.BytesIO(replacement)) as check:
                for index in range(check.n_frames):
                    check.seek(index)
                    check.convert('RGB').load()
            PANORAMA.write_bytes(replacement)
            print(f'Repaired panorama GIF: {len(frames)} frames, {len(replacement)} bytes')
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = previous


def main() -> None:
    repair_panorama_if_needed()
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
    svg = add_background(render_card(payload), weather_background(light=False)) if payload is not None else dark_source
    OUTPUT.write_text(svg, encoding='utf-8')
    write_slices(svg, OUTPUT)
    light_svg = add_background(light_card(render_card(payload)), weather_background(light=True), light=True) if payload is not None else light_source
    light_output.write_text(light_svg, encoding='utf-8')
    write_slices(light_svg, light_output)
    if payload is not None:
        for light in (False, True):
            top, bottom = raster_weather_cards(payload, light=light)
            prefix = 'weather-azumino-light' if light else 'weather-azumino'
            (OUTPUT.parent / (prefix + '-top.gif')).write_bytes(top)
            (OUTPUT.parent / (prefix + '-bottom.gif')).write_bytes(bottom)
    print(f'Updated weather in both themes; panorama={PANORAMA.exists()}')


if __name__ == '__main__':
    main()


