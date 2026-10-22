#!/usr/bin/env python3
"""Extract the upstream language donut and legend into the profile card."""
from __future__ import annotations

import copy
from profile_slices import write_slices
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'profile-3d-contrib' / 'profile-night-view.svg'
NS = 'http://www.w3.org/2000/svg'
TAG = '{' + NS + '}'
ET.register_namespace('', NS)


def customize_svg(svg: str) -> str:
    source = ET.fromstring(svg)
    # Identify the donut by its titled language slices, independently of position.
    donut = next((g for g in source.iter(TAG+'g')
                  if len(g.findall(TAG+'path/'+TAG+'title')) >= 2), None)
    if donut is None:
        raise ValueError('Could not identify the upstream language donut')
    parents = {child: parent for parent in source.iter() for child in parent}
    language = parents[donut]
    legend = next((g for g in language.findall(TAG+'g') if g is not donut
                   and g.findall(TAG+'text')), None)
    if legend is None:
        raise ValueError('Could not identify the upstream language legend')
    root = ET.Element(TAG+'svg', {
        'id': 'ryouy-language-card', 'width': '254', 'height': '145.8857142857143',
        'viewBox': '0 0 254 145.8857142857143', 'role': 'img', 'aria-label': 'GitHub language distribution',
    })
    ET.SubElement(root, TAG+'title').text = 'Languages'
    ET.SubElement(root, TAG+'style').text = (
        'text{font-family:Arial,Helvetica,sans-serif}.fill-fg{fill:#b4c7d7}'
        '.stroke-bg{stroke:#101b2b}'
    )
    ET.SubElement(root, TAG+'rect', {'x': '.75', 'y': '.75', 'width': '252.5',
        'height': '144.3857142857143', 'rx': '12', 'fill': '#101b2b', 'stroke': '#2a3e54', 'stroke-width': '1.5'})
    ET.SubElement(root, TAG+'text', {'x': '136', 'y': '25', 'fill': '#f7fbff',
        'font-size': '14', 'font-weight': '600'}).text = 'Languages'
    # Preserve all upstream slices, labels and tooltips; only their placement changes.
    chart = copy.deepcopy(donut)
    chart.set('transform', 'translate(65 73) scale(.48)')
    labels = copy.deepcopy(legend)
    labels.set('transform', 'translate(136 41)')
    for index, (box, text) in enumerate(zip(labels.findall(TAG+'rect'), labels.findall(TAG+'text'))):
        box.attrib.update(x='0', y=f'{index*16:g}', width='8', height='8')
        text.attrib.update(x='12', y=f'{index*16+4:g}')
        text.set('font-size', '11px')
        if text.text == 'Jupyter Notebook':
            text.text = 'Jupyter'
    root.extend([chart, labels])
    # A stable final frame avoids the old delayed fade on mobile SVG renderers.
    for parent in root.iter():
        for child in list(parent):
            if child.tag in {TAG+'animate', TAG+'animateTransform'}:
                parent.remove(child)
    return ET.tostring(root, encoding='unicode') + '\n'


def apply_rounding() -> None:
    svg = customize_svg(TARGET.read_text(encoding='utf-8'))
    TARGET.write_text(svg, encoding='utf-8')
    write_slices(svg, TARGET)
    print('Updated language-only profile card')


if __name__ == '__main__':
    apply_rounding()
