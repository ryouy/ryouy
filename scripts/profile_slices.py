"""Export matching SVG half-panels for the border-free README grid."""
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

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
