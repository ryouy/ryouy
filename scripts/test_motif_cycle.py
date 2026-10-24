import re
import unittest
import xml.etree.ElementTree as ET
from generate_motif_cycle import MOTIFS,compose,compact_keyframes
from generate_snake_duet import TAG,restart_pixels
from test_snake_duet import fixture

class MotifTests(unittest.TestCase):
    def test_all_short_phrases_fit_the_grid(self):
        for motif,phrase in MOTIFS:
            pixels=restart_pixels(53,7,phrase)
            self.assertGreater(len(pixels),50,motif)
            self.assertTrue(all(0<=x<53 and 0<=y<7 for x,y in pixels))
    def test_six_whole_rounds_have_unique_styles_and_matching_models(self):
        svg=compose(fixture(),42);root=ET.fromstring(svg)
        scenes=root.findall(TAG+'g/'+TAG+'svg')
        self.assertEqual(len(scenes),6)
        self.assertEqual({r.get('data-motif') for r in scenes},{m for m,_ in MOTIFS})
        ids=[e.get('id') for e in root.iter() if e.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        durations=[]
        for scene in scenes:
            css=scene.find(TAG+'style').text
            self.assertNotIn('#'+scene.get('id')+' @keyframes',css)
            self.assertIn('@keyframes '+scene.get('id')+'-',css)
            self.assertNotIn(':root',css)
            self.assertGreaterEqual(int(scene.get('data-entry-gap-ms')),1200)
            durations+=re.findall(r'animation-duration:([\d.]+)ms',css)
            for phase in ['red','blue']:
                group=scene.find(TAG+f"g[@class='duet-{phase}']")
                self.assertEqual(len(group),2)
                for actor in group:
                    self.assertEqual(len(actor),4)
                    self.assertEqual(actor[0].tag,TAG+('rect' if scene.get('data-motif')=='snake' else 'svg'))
        self.assertEqual(len(set(durations)),1)
        self.assertEqual(svg,compose(fixture(),42))
        self.assertNotEqual(root.get('data-motif-order'),','.join(m for m,_ in MOTIFS))
    def test_compression_preserves_holds_and_change_boundaries(self):
        css='@keyframes x{0%{opacity:0}10%{opacity:0}20%{opacity:0}30%{opacity:1}100%{opacity:1}}'
        compact=compact_keyframes(css)
        self.assertNotIn('10.000000%',compact)
        for t in ['0.000000','20.000000','30.000000','100.000000']:self.assertIn(t+'%',compact)
