import unittest
import xml.etree.ElementTree as ET
from round_contrib_svg import customize_svg, TAG
from profile_slices import light_card

def source(names):
    chart=''.join(f'<path d="M0 0 L10 0 L0 10Z" fill="#4593f8"><title>{n}</title></path>' for n in names)
    legend=''.join(f'<rect width="8" height="8"/><text>{n}</text>' for n in names)
    return f'<svg xmlns="http://www.w3.org/2000/svg"><g><g>{chart}<animate attributeName="opacity"/></g><g>{legend}</g></g></svg>'

class LanguageCardTests(unittest.TestCase):
    def test_one_language_still_generates_a_card(self):
        root=ET.fromstring(customize_svg(source(['Python'])))
        self.assertEqual(len(list(root.iter(TAG+'path'))),1)
        self.assertIn('Python',''.join(root.itertext()))
        self.assertFalse(list(root.iter(TAG+'animate')))
    def test_multiple_languages_preserve_slices_and_jupyter_abbreviation(self):
        root=ET.fromstring(customize_svg(source(['Python','Jupyter Notebook'])))
        self.assertEqual(len(list(root.iter(TAG+'path'))),2)
        labels=[e.text for e in root.iter(TAG+'text')]
        self.assertIn('Jupyter',labels)
    def test_missing_chart_fails_before_publishing(self):
        with self.assertRaisesRegex(ValueError,'donut'):customize_svg(source([]))

    def test_light_palette_preserves_language_data(self):
        light = light_card(customize_svg(source(['Python', 'JavaScript'])))
        self.assertIn('.fill-fg{fill:#57606a}', light)
        self.assertIn('.stroke-bg{stroke:#ffffff}', light)
        self.assertIn('fill="#24292f"', light)
        self.assertIn('Python', light)
        ET.fromstring(light)
