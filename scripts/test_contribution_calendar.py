import unittest
import xml.etree.ElementTree as ET
from contribution_calendar import parse_calendar,add_calendar_labels,TAG

HTML='''<h2 id="js-contribution-activity-description">1,234 contributions in the last year</h2>
<td class="ContributionCalendar-label" colspan="2"><span class="sr-only">December</span><span aria-hidden="true">Dec</span></td>
<td class="ContributionCalendar-label" colspan="1"><span class="sr-only">January</span><span aria-hidden="true">Jan</span></td>
<td data-date="2025-12-28" data-ix="0"></td><td data-date="2026-01-12" data-ix="2"></td>'''

def source():
    root=ET.Element(TAG+'svg',{'viewBox':'1.5 -32 45 158','width':'45','height':'158'})
    for x in range(3):
        for y in range(7):ET.SubElement(root,TAG+'rect',{'class':'c','x':str(2+x*16),'y':str(2+y*16)})
    return ET.tostring(root,encoding='unicode')

class CalendarTests(unittest.TestCase):
    def test_native_total_and_month_columns_survive_year_boundary(self):
        c=parse_calendar(HTML)
        self.assertEqual(c['total'],1234)
        self.assertEqual(c['months'],[{'week':0,'label':'Dec'},{'week':2,'label':'Jan'}])
    def test_unlabeled_partial_month_does_not_shorten_the_grid(self):
        # GitHub may omit the short first month's header, while retaining its day cells.
        html=HTML.replace('data-ix="2"', 'data-ix="3"')
        self.assertEqual(parse_calendar(html)['columns'],4)
    def test_only_requested_labels_and_total_are_visible(self):
        for dark in [False,True]:
            root=ET.fromstring(add_calendar_labels(source(),parse_calendar(HTML),dark))
            texts=[x.text for x in root.iter(TAG+'text')]
            self.assertEqual(texts,['1,234 contributions in the last year','Mon','Wed','Fri','Dec','Jan'])
            self.assertEqual(root.get('data-contribution-total'),'1234')
            self.assertEqual(len([x for x in root.iter(TAG+'rect') if x.get('class')=='c']),21)
            self.assertIsNotNone(root.find(TAG+"g[@clip-path='url(#calendar-grid-clip)']"))
    def test_malformed_or_misaligned_data_does_not_publish(self):
        with self.assertRaises(ValueError):parse_calendar('<html>Rate limited</html>')
        c=parse_calendar(HTML);c['columns']=4
        with self.assertRaisesRegex(ValueError,'dimensions'):add_calendar_labels(source(),c)
