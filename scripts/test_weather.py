import copy
import unittest
import xml.etree.ElementTree as ET
from update_weather import render_card, format_temperature
from profile_slices import light_card

PAYLOAD = {
    'current': {'time': '2026-12-31T23:45', 'temperature_2m': -2.5, 'weather_code': 71},
    'daily': {'time': ['2026-12-31','2027-01-01'], 'weather_code': [71,0],
              'temperature_2m_max': [1,3], 'temperature_2m_min': [-5,-4]},
}
class WeatherTests(unittest.TestCase):
    def text(self,payload):return ''.join(ET.fromstring(render_card(payload)).itertext())
    def test_year_boundary_and_negative_temperatures(self):
        text=self.text(PAYLOAD)
        self.assertIn('Clear sky',text);self.assertIn('High 3° / Low -4°',text)
    def test_nulls_short_arrays_and_missing_forecast_remain_readable(self):
        for daily in [None, {}, {'time':['2026-12-31']}, {'time':['2026-12-31','2027-01-01'],'weather_code':[None]}]:
            p=copy.deepcopy(PAYLOAD);p['daily']=daily;p['current']['temperature_2m']=None;p['current']['weather_code']=None
            text=self.text(p)
            self.assertIn('Unavailable',text);self.assertIn('High — / Low —',text)
            self.assertNotIn('None',text);self.assertNotIn('nan',text)
    def test_nonfinite_temperatures_are_not_published(self):
        for value in [None,float('nan'),float('inf'),True,'12']:
            self.assertEqual(format_temperature(value),'—')

    def test_light_palette_and_forecast(self):
        light = light_card(render_card(PAYLOAD))
        self.assertIn('stop-color="#ffffff"', light)
        self.assertIn('fill="#24292f"', light)
        self.assertIn('High 3° / Low -4°', light)
        self.assertNotIn('stop-color="#132235"', light)
        ET.fromstring(light)
