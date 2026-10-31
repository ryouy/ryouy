"""Export matching SVG half-panels for the border-free README grid."""
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

def style_card(svg: str) -> str:
    """Give the profile cards a quiet shared surface and a small alpine signature."""
    tag = '{http://www.w3.org/2000/svg}'
    root = ET.fromstring(svg)
    if root.find(".//" + tag + "linearGradient[@id='profile-card-surface']") is not None:
        return svg
    background = next((el for el in root.iter(tag+'rect')
                       if el.get('fill') == '#101b2b' and el.get('stroke')), None)
    if background is None:
        raise ValueError('Profile card background was not found')
    defs = ET.Element(tag+'defs')
    for name, stops in [('surface', [('#132235', '0%'), ('#0e1826', '100%')]),
                        ('rim', [('#354c62', '0%'), ('#223449', '100%')])]:
        gradient = ET.SubElement(defs, tag+'linearGradient', {
            'id': 'profile-card-'+name, 'x1': '0%', 'y1': '0%', 'x2': '100%', 'y2': '100%'})
        for color, offset in stops:
            ET.SubElement(gradient, tag+'stop', {'offset': offset, 'stop-color': color})
    root.insert(0, defs)
    background.set('fill', 'url(#profile-card-surface)')
    background.set('stroke', 'url(#profile-card-rim)')
    background.set('stroke-width', '1')
    right = float(background.get('x', '0')) + float(background.get('width'))
    top = float(background.get('y', '0'))
    # A tiny ridge fits above every card's existing content.
    ridge = ET.Element(tag+'polyline', {
        'points': f'{right-40:g},{top+11:g} {right-33:g},{top+5:g} {right-28:g},{top+9:g} {right-23:g},{top+6:g} {right-16:g},{top+11:g}',
        'fill': 'none', 'stroke': '#8db7ca', 'stroke-width': '.85',
        'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'opacity': '.48',
        'aria-hidden': 'true'})
    parent = next(el for el in root.iter() if background in list(el))
    parent.insert(list(parent).index(background)+1, ridge)
    return ET.tostring(root, encoding='unicode') + '\n'


def light_card(svg: str) -> str:
    """Use a readable light palette while retaining the dark card's geometry."""
    palette = {
        '#132235': '#ffffff',
        '#0e1826': '#f6f8fa',
        '#354c62': '#d0d7de',
        '#223449': '#d8dee4',
        '#8db7ca': '#6c9db9',
        '#f7fbff': '#24292f',
        '#8abfe5': '#0969da',
        '#879fb2': '#57606a',
        '#314558': '#d0d7de',
        '#d2e1ed': '#424a53',
        '#b6cadb': '#57606a',
        '#b4c7d7': '#57606a',
        '#101b2b': '#ffffff',
        '#2a3e54': '#d0d7de',
    }
    for dark, light in palette.items():
        svg = svg.replace(dark, light)
    return svg

def write_slices(svg: str, target: Path) -> None:
    root = ET.fromstring(svg)
    x, y, width, height = map(float, root.get('viewBox').split())
    for name, offset in [('top', 0), ('bottom', height / 2)]:
        panel = copy.deepcopy(root)
        panel.set('viewBox', f'{x:g} {y + offset:g} {width:g} {height / 2:g}')
        panel.set('width', f'{width:g}')
        panel.set('height', f'{height / 2:g}')
        target.with_name(target.stem + '-' + name + target.suffix).write_text(
            ET.tostring(panel, encoding='unicode') + '\n', encoding='utf-8')

