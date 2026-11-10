from pathlib import Path
from html import unescape
from html.parser import HTMLParser
import json,re,shutil
from urllib.parse import unquote,urlparse
from decimal import Decimal,ROUND_HALF_UP

ROOT=Path.cwd()
DESKTOP=Path('C:/Users/Aorus Ryzen/Desktop')
SOURCES=['RtH2FT','VnjZxr','BRMbt6','kZjZxr','9HbKHx']
class Node:
 def __init__(self,tag='',attrs=(),parent=None):
  self.tag,self.attrs,self.parent,self.children=tag,dict(attrs),parent,[]
 def all(self,tag=None,cls=None):
  result=[]
  for c in self.children:
   if isinstance(c,Node):
    if (tag is None or c.tag==tag) and (cls is None or cls in c.attrs.get('class','').split()): result.append(c)
    result.extend(c.all(tag,cls))
  return result
 def text(self):
  return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split())
class Parser(HTMLParser):
 def __init__(self):
  super().__init__();self.root=Node();self.current=self.root
 def handle_starttag(self,tag,attrs):
  n=Node(tag,attrs,self.current);self.current.children.append(n)
  if tag not in ('img','meta','link','br','hr','input','source','wbr','area','base','embed','param','col'): self.current=n
 def handle_endtag(self,tag):
  n=self.current
  while n.parent:
   if n.tag==tag:self.current=n.parent;return
   n=n.parent
 def handle_data(self,data):self.current.children.append(data)
out=ROOT/'data/pcpartpicker';out.mkdir(parents=True,exist_ok=True)
builds=[];products={}
for file in DESKTOP.glob('*PCPartPicker.html'):
 html=file.read_text(encoding='utf-8')
 match=re.search(r'saved from url=.*?https://pcpartpicker.com/b/([A-Za-z0-9]+)',html)
 if not match or match[1] not in SOURCES:continue
 parser=Parser();parser.feed(html);root=parser.root
 table=next(t for t in root.all('table') if 'partlist' in t.attrs.get('class','').split())
 parts=[];cat=''
 for row in table.all('tr'):
  cs=row.all(cls='td__component')
  if cs:cat=cs[0].text()
  names=row.all(cls='td__name')
  if not names:continue
  links=[n for n in names[0].all('a') if '/product/' in n.attrs.get('href','')]
  if not links:continue
  link=links[0];url=link.attrs['href'];pid=urlparse(url).path.split('/')[2]
  imgs=row.all('img')
  name=imgs[0].attrs.get('alt') if imgs else link.text()
  prices=row.all(cls='td__price')
  raw=prices[0].text() if prices else ''
  pm=re.search(r'\$([\d,]+(?:\.\d+)?)',raw)
  usd=Decimal(pm[1].replace(',','')) if pm else None
  image=imgs[0].attrs.get('src','') if imgs else ''
  item={'source_id':pid,'category_en':cat,'name_en':name or link.text(),'source_url':url,'price_usd':str(usd) if usd is not None else None,'price_vnd':int((usd*26000).quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if usd is not None else None,'price_original_text':raw,'image_saved_path':image,'build_id':match[1]}
  parts.append(item)
  if pid not in products:products[pid]=dict(item,build_ids=[match[1]],image_file_name=file.name)
  elif match[1] not in products[pid]['build_ids']:products[pid]['build_ids'].append(match[1])
 title=root.all('title')[0].text()
 build_imgs=[n.attrs.get('src','') for n in root.all('img') if 'build' in n.attrs.get('class','') or '/build/' in n.attrs.get('src','')]
 builds.append({'id':match[1],'source_url':'https://pcpartpicker.com/b/'+match[1],'title_en':title,'html_file':file.name,'parts':parts})
(out/'extracted-builds.json').write_text(json.dumps(builds,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'extracted-products.json').write_text(json.dumps(list(products.values()),ensure_ascii=False,indent=2),encoding='utf-8')
for b in builds:
 print('BUILD',b['id'],b['title_en'])
 for p in b['parts']:print(p['source_id'],p['category_en'],p['name_en'],p['price_usd'])
print('BUILDS',len(builds),'UNIQUE PRODUCTS',len(products))
