"""Read GitHub's public calendar and add its heading/month/weekday labels."""
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.request import Request,urlopen

TAG='{http://www.w3.org/2000/svg}'

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__();self.heading=False;self.heading_text=[];self.month=None;self.month_visible=False
        self.months=[];self.week=0;self.days=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h2' and a.get('id')=='js-contribution-activity-description':self.heading=True
        if tag=='td' and a.get('colspan') and 'ContributionCalendar-label' in a.get('class',''):
            self.month={'week':self.week,'span':int(a['colspan']),'label':''}
        if tag=='span' and self.month is not None and a.get('aria-hidden')=='true':self.month_visible=True
        if tag=='td' and a.get('data-date'):
            self.days.append({'date':a['data-date'],'week':int(a['data-ix'])})
    def handle_endtag(self,tag):
        if tag=='h2':self.heading=False
        if tag=='span':self.month_visible=False
        if tag=='td' and self.month is not None:
            self.months.append({'week':self.month['week'],'label':self.month['label'].strip()})
            self.week+=self.month['span'];self.month=None
    def handle_data(self,data):
        if self.heading:self.heading_text.append(data)
        if self.month_visible:self.month['label']+=data
    def result(self):
        heading=' '.join(' '.join(self.heading_text).split())
        match=re.fullmatch(r'([\d,]+) contributions? in the last year',heading)
        if not match or not self.days or not self.months or any(not m['label'] for m in self.months):
            raise ValueError('GitHub contribution calendar markup was not recognized')
        return {'heading':heading,'total':int(match[1].replace(',','')),'months':self.months,
                'columns':self.week,'days':self.days}

def parse_calendar(html):
    parser=CalendarParser();parser.feed(html);return parser.result()

def fetch_calendar(username):
    if not re.fullmatch(r'[A-Za-z0-9-]+',username):raise ValueError('Invalid GitHub username')
    request=Request(f'https://github.com/users/{username}/contributions',headers={'User-Agent':'ryouy-profile-calendar/1.0'})
    with urlopen(request,timeout=25) as response:return parse_calendar(response.read().decode('utf-8'))

def add_calendar_labels(svg,calendar,dark=False):
    root=ET.fromstring(svg)
    cells=[e for e in root.findall(TAG+'rect') if 'c' in e.get('class','').split()]
    xs=sorted({float(e.get('x')) for e in cells});ys=sorted({float(e.get('y')) for e in cells})
    if len(xs)!=calendar['columns'] or len(ys)!=7:raise ValueError('Calendar labels do not match the snake grid dimensions')
    # Match the default dark calendar, rather than Platane/snk's teal palette.
    if dark:
        style=root.find(TAG+'style')
        if style is not None and style.text:
            palette={'--cb':'#0104090d','--ce':'#151b23','--c0':'#151b23',
                     '--c1':'#033a16','--c2':'#196c2e','--c3':'#2ea043','--c4':'#56d364'}
            for name,color in palette.items():
                style.text=re.sub(re.escape(name)+r':[^;}]+',name+':'+color,style.text)
    old_view=list(map(float,root.get('viewBox').split()));left=xs[0]-40;top=ys[0]-56
    right=old_view[0]+old_view[2];bottom=old_view[1]+old_view[3]
    root.set('viewBox',f'{left:g} {top:g} {right-left:g} {bottom-top:g}')
    root.set('width',f'{right-left:g}');root.set('height',f'{bottom-top:g}')
    root.set('data-contribution-total',str(calendar['total']))
    root.set('data-calendar-start',min(d['date'] for d in calendar['days']))
    root.set('data-calendar-end',max(d['date'] for d in calendar['days']))
    defs=ET.SubElement(root,TAG+'defs');clip=ET.SubElement(defs,TAG+'clipPath',{'id':'calendar-grid-clip'})
    ET.SubElement(clip,TAG+'rect',{'x':str(xs[0]-.5),'y':str(ys[0]-.5),
        'width':str(xs[-1]-xs[0]+13),'height':str(ys[-1]-ys[0]+13)})
    drawing=ET.Element(TAG+'g',{'clip-path':'url(#calendar-grid-clip)'})
    for child in list(root):
        if child.tag in {TAG+'g',TAG+'rect'}:root.remove(child);drawing.append(child)
    root.append(drawing)
    labels=ET.SubElement(root,TAG+'g',{'class':'calendar-labels','font-family':'-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif',
        'fill':'#9198a1' if dark else '#59636e','font-size':'13'})
    heading=ET.SubElement(labels,TAG+'text',{'x':str(left+2),'y':str(ys[0]-34),'font-size':'17',
        'fill':'#f0f6fc' if dark else '#1f2328'})
    heading.text=calendar['heading']
    for row,name in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:
        ET.SubElement(labels,TAG+'text',{'x':str(left+2),'y':str(ys[row]+10)}).text=name
    for month in calendar['months']:
        ET.SubElement(labels,TAG+'text',{'x':str(xs[month['week']]),'y':str(ys[0]-12),'fill':'#f0f6fc' if dark else '#1f2328'}).text=month['label']
    ET.SubElement(root,TAG+'desc').text=calendar['heading']+'. Months and Mon, Wed, Fri labels follow the GitHub calendar.'
    return ET.tostring(root,encoding='unicode')+'\n'
