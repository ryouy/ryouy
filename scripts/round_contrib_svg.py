#!/usr/bin/env python3
"""Simplify and round the generated 3D contribution card after every update.

Keep the contribution calendar, language donut and total. Remove the radar
chart and star/fork counters structurally, retaining the generator's data.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'profile-3d-contrib' / 'profile-night-view.svg'
CLIP_ID = 'ryouy-rounded-3d-frame'
TOTAL_ID = 'ryouy-contribution-total'
NS = 'http://www.w3.org/2000/svg'
TAG = '{' + NS + '}'
ET.register_namespace('', NS)


def customize_svg(svg: str) -> str:
    root = ET.fromstring(svg)
    if 'viewBox' not in root.attrib:
        raise ValueError('3D contribution SVG is missing its viewBox')
    parents = {child: parent for parent in root.iter() for child in parent}
    radar_groups = {parents[el] for el in root.iter(TAG + 'polygon')
                    if 'radar' in el.get('class', '').split()}
    for group in radar_groups:
        parents[group].remove(group)
    style = root.find(TAG + 'style')
    if style is None:
        raise ValueError('3D contribution SVG is missing its root stylesheet')
    style.text = re.sub(r'\.radar\s*\{[^}]*\}', '', style.text or '')

    if not any(el.get('id') == TOTAL_ID for el in root.iter()):
        footer = next((group for group in root.iter(TAG + 'g')
                       if any(el.tag == TAG + 'text' and (el.text or '').strip() == 'contributions'
                              for el in group)), None)
        if footer is None:
            raise ValueError('Could not identify the contribution summary footer')
        items = list(footer)
        label = next(el for el in items if el.tag == TAG + 'text'
                     and (el.text or '').strip() == 'contributions')
        count = items[items.index(label) - 1]
        if count.tag != TAG + 'text' or not (count.text or '').strip().isdigit():
            raise ValueError('Could not identify the total contribution count')
        # Icon groups in this footer are the star and fork. Each has a count.
        icons = [el for el in items if el.tag == TAG + 'g' and el.find(TAG + 'path') is not None]
        if len(icons) != 2:
            raise ValueError('Expected the star and fork icon groups')
        for icon in icons:
            number = items[items.index(icon) + 1]
            if number.tag != TAG + 'text' or number.find(TAG + 'title') is None:
                raise ValueError('Expected a star/fork count after its icon')
            footer.remove(icon)
            footer.remove(number)
        x, _, width, _ = map(float, root.get('viewBox').split())
        total = ET.Element(TAG + 'text', {
            'id': TOTAL_ID, 'x': f'{x + width/2:g}', 'y': count.get('y', '830'),
            'text-anchor': 'middle',
        })
        value = ET.SubElement(total, TAG + 'tspan', {
            'class': 'fill-strong', 'font-size': '32px', 'font-weight': 'bold',
        })
        value.text = count.text
        suffix = ET.SubElement(total, TAG + 'tspan', {
            'class': 'fill-fg', 'font-size': '24px', 'dx': '8',
        })
        suffix.text = 'contributions'
        footer.remove(count)
        footer.remove(label)
        footer.insert(0, total)

    if not any(el.get('id') == CLIP_ID for el in root.iter()):
        x, y, width, height = map(float, root.get('viewBox').split())
        radius = round(min(width, height)*.03, 1)
        defs = ET.SubElement(root, TAG + 'defs')
        clip = ET.SubElement(defs, TAG + 'clipPath', {'id': CLIP_ID})
        ET.SubElement(clip, TAG + 'rect', {
            'x': f'{x:g}', 'y': f'{y:g}', 'width': f'{width:g}', 'height': f'{height:g}',
            'rx': f'{radius:g}', 'ry': f'{radius:g}',
        })
        content = [el for el in root if el.tag not in
                   {TAG+'style', TAG+'defs', TAG+'title', TAG+'desc'}]
        frame = ET.SubElement(root, TAG + 'g', {'clip-path': f'url(#{CLIP_ID})'})
        for el in content:
            root.remove(el)
            frame.append(el)
    return ET.tostring(root, encoding='unicode') + '\n'


def apply_rounding() -> None:
    TARGET.write_text(customize_svg(TARGET.read_text(encoding='utf-8')), encoding='utf-8')
    print('Simplified 3D card: no radar or star/fork counts; rounded corners retained')


if __name__ == '__main__':
    apply_rounding()
