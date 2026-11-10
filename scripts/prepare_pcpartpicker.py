"""Prepare Vietnamese sample data from the five saved PCPartPicker builds.
Run from repository root after scripts/extract_pcpartpicker.py.
Only specifications explicitly present in saved product names are extracted.
"""
from pathlib import Path
from urllib.parse import unquote
from decimal import Decimal
from collections import Counter
import json,re,shutil,csv

root=Path.cwd()
folder=root/'data/pcpartpicker'
desktop=Path('C:/Users/Aorus Ryzen/Desktop')
builds=json.loads((folder/'extracted-builds.json').read_text(encoding='utf8'))
raw=json.loads((folder/'extracted-products.json').read_text(encoding='utf8'))
categories={
'CPU':('cpu','Bộ xử lý'),'CPU Cooler':('cooler','Tản nhiệt CPU'),
'Motherboard':('mainboard','Bo mạch chủ'),'Memory':('ram','Bộ nhớ RAM'),
'Video Card':('gpu','Card đồ họa'),'Case':('case','Vỏ máy tính'),
'Power Supply':('psu','Bộ nguồn'),'Case Fan':('fan','Quạt vỏ máy'),
'Monitor':('monitor','Màn hình'),'Keyboard':('keyboard','Bàn phím'),
'Mouse':('mouse','Chuột'),'Headphones':('headphones','Tai nghe'),
'Operating System':('license','Bản quyền hệ điều hành'),
'Optical Drive':('optical_drive','Ổ đĩa quang'),
'Wireless Network Adapter':('network_adapter','Card mạng Wi-Fi'),
'Fan Controller':('fan_controller','Bộ điều khiển quạt'),
'Custom':('expansion_card','Card mở rộng USB')}
required={
'cpu':['socket','cores','threads','boost_ghz','tdp_w','has_igpu','stock_cooler'],
'mainboard':['socket','chipset','form_factor','ram_type','ram_slots','max_ram_gb','m2_slots'],
'ram':['ram_type','capacity_gb','modules','speed_mhz'],
'gpu':['chip','vram_gb','tdp_w','length_mm'],
'cooler':['cooler_type','sockets','height_mm','tdp_w'],
'ssd':['interface','capacity_gb','pcie_gen'],
'psu':['watt','efficiency','modular'],
'case':['supported_mb','max_gpu_length_mm','max_cooler_height_mm']}
def find(pattern,text,cast=str):
 m=re.search(pattern,text,re.I)
 return cast(m[1]) if m else None
def specs_for(cat,n):
 s={k:None for k in required.get(cat,[])}
 if cat=='cpu':
  s['cores']=find(r'(\d+)-Core',n,int)
  s['base_ghz']=find(r'([\d.]+) GHz',n,float)
 if cat=='mainboard':
  s['socket']=find(r'(LGA\d+|AM5|AM4)',n)
  s['chipset']=find(r'\b(Z\d{3}|[BX]\d{3}E?)',n)
  s['form_factor']=find(r'(ATX|Micro ATX|Mini ITX)',n)
 if cat=='ram':
  s.update(capacity_gb=find(r'(\d+) GB',n,int),modules=find(r'\((\d+) x',n,int),
           ram_type=find(r'(DDR[345])',n),speed_mhz=find(r'DDR[345]-(\d+)',n,int),
           cas_latency=find(r'CL(\d+)',n,int))
 if cat in ('ssd','hdd'):
  value=find(r'([\d.]+) (?:GB|TB)',n,Decimal)
  s['capacity_gb']=int(value*(1000 if re.search(r'[\d.] TB',n) else 1)) if value is not None else None
  s['form_factor']=find(r'(M\.2-\d+|2\.5\"|3\.5\")',n)
  s['interface']='NVMe' if 'NVME' in n.upper() else None
  s['pcie_gen']=find(r'PCIe (\d+)\.',n,int)
  if cat=='hdd':s['rpm']=find(r'(\d+) RPM',n,int)
 if cat=='gpu':
  s['chip']=find(r'((?:GeForce|Radeon) .+?) \d+ GB',n)
  s['vram_gb']=find(r'(\d+) GB',n,int)
 if cat=='psu':
  s.update(watt=find(r'(\d+) W',n,int),efficiency=find(r'(80\+\s*(?:Bronze|Silver|Gold|Platinum|Titanium)?)',n),
           modular=True if 'Modular' in n else None)
 if cat=='cooler':
  s['cooler_type']='liquid' if 'Liquid' in n else 'air'
  s['airflow_cfm']=find(r'([\d.]+) CFM',n,float)
 if cat=='case':s['form_factor']=find(r'(ATX (?:Full|Mid) Tower)',n)
 if cat=='fan':
  s.update(diameter_mm=find(r'(\d+) mm',n,int),airflow_cfm=find(r'([\d.]+) CFM',n,float),
           pack_quantity=find(r'(\d+)-Pack',n,int) or 1)
 if cat=='monitor':
  s.update(diagonal_inches=find(r'([\d.]+)\"',n,float),resolution=find(r'(\d+x\d+)',n),
           refresh_hz=find(r'(\d+) Hz',n,int))
 if cat in ('keyboard','mouse'):
  s['connectivity']=[x for x in ('Bluetooth','Wireless','Wired') if re.search(r'\b'+x+r'\b',n)]
 return s

replacements=[
('Fully Modular','dây cáp tháo rời hoàn toàn'),('ATX Mid Tower Case','ATX tháp trung'),
('ATX Full Tower Case','ATX tháp lớn'),('Liquid CPU Cooler','tản nhiệt nước'),
('CPU Cooler','tản nhiệt CPU'),('Solid State Drive','ổ SSD'),('Internal Hard Drive','ổ cứng HDD'),
('Power Supply','bộ nguồn'),('Motherboard','bo mạch chủ'),('Video Card','card đồ họa'),
('Processor','bộ xử lý'),('Memory','RAM'),('Case Fans','quạt vỏ máy'),('Case Fan','quạt vỏ máy'),
('Wireless Network Adapter','card mạng không dây'),('Fan Controller','bộ điều khiển quạt'),
('Headphones','tai nghe'),('Keyboard','bàn phím'),('Mouse','chuột'),
('Blu-Ray/DVD/CD Writer','ổ ghi Blu-ray/DVD/CD'),('Monitor','màn hình'),
('Sleeve Bearing','vòng bi bạc trượt'),('Retail - USB 64-bit','bản bán lẻ USB 64 bit'),
('Bluetooth/Wireless/Wired','Bluetooth/không dây/có dây'),
('Wireless/Wired','không dây/có dây'),('Wired','có dây'),('Optical','quang học'),
('Standard','tiêu chuẩn'),('with Acronis Data Recovery','kèm Acronis Data Recovery'),
('for Xbox Series X | S','dành cho Xbox Series X | S')]
def translate(n):
 for a,b in replacements:n=n.replace(a,b)
 n=re.sub(r'(\d+)-Core',r'\1 nhân',n)
 n=re.sub(r'(\d+)-Pack',r'bộ \1 chiếc',n)
 return n.replace('\ufffd','').strip()

products=[]
assets=root/'public/images/pcpartpicker';assets.mkdir(parents=True,exist_ok=True)
for p in raw:
 pid=p['source_id'];n=p['name_en']
 cat,label=categories.get(p['category_en'],('hdd','Ổ cứng HDD') if 'RPM' in n else ('ssd','Ổ cứng SSD'))
 observations=[dict(build_id=b['id'],price_usd=x['price_usd'],price_vnd=x['price_vnd'])
               for b in builds for x in b['parts'] if x['source_id']==pid]
 priced=next((o for o in observations if o['price_usd'] is not None),None)
 img_source=(desktop/unquote(p['image_saved_path'])).resolve()
 image=''
 if desktop.resolve() not in img_source.parents:raise ValueError('Unsafe image path')
 if img_source.is_file():
  sig=img_source.read_bytes()[:12]
  ext='.jpg' if sig.startswith(b'\xff\xd8\xff') else '.png' if sig.startswith(b'\x89PNG') else '.webp' if sig.startswith(b'RIFF') and sig[8:12]==b'WEBP' else None
  if ext:
   shutil.copyfile(img_source,assets/(pid+ext));image='/images/pcpartpicker/'+pid+ext
 specs=specs_for(cat,n)
 name=label+' '+translate(n)
 description='Dữ liệu mẫu lấy từ cấu hình PCPartPicker. '+('Giá quy đổi từ USD theo 1 USD = 26.000 VNĐ; không phải báo giá bán tại Việt Nam.' if priced else 'Chưa có giá trong HTML nguồn; không dùng để tư vấn ngân sách hoặc bán hàng.')+' Thông số chưa xác minh được để trống. Tồn kho giả lập phục vụ đồ án.'
 display_cat='Thiết bị ngoại vi' if cat in ('expansion_card','keyboard','headphones','monitor','network_adapter','optical_drive') else 'Tản nhiệt' if cat in ('fan','fan_controller') else cat
 products.append(dict(id='pcpp-'+pid,sku='PCPP-'+pid.upper(),cat=display_cat,product_type=cat,name=name,
  brand=n.split()[0] if cat!='expansion_card' else 'Không xác định',
  description=description,price=priced['price_vnd'] if priced else 0,
  stock=10 if priced else 0,active=bool(priced),img=image,specs=specs,
  attributes=[{'name':k,'value':str(v)} for k,v in specs.items() if v is not None],
  source=dict(url=p['source_url'],name_en=n,build_ids=p['build_ids'],exchange_rate_vnd_per_usd=26000,
              price_usd=priced['price_usd'] if priced else None,price_status='quoted' if priced else 'missing',
              price_observations=observations,spec_basis='Thông số được ghi trực tiếp trong tên sản phẩm nguồn',
              stock_is_demo=True,unknown_spec_keys=[k for k,v in specs.items() if v is None])))
titles={'BRMbt6':'Máy trạm CAD kết hợp chơi game (2021)','VnjZxr':'Cấu hình đỉnh cao',
'9HbKHx':'Lần đầu tự lắp máy','RtH2FT':'Máy tính chơi game đầu tiên','kZjZxr':'THE MIKU DESTROYER — cấu hình chủ đề Hatsune Miku'}
result=[]
for b in builds:
 counts=Counter(x['source_id'] for x in b['parts'])
 subtotal=sum(x['price_vnd'] or 0 for x in b['parts'])
 missing=[x['source_id'] for x in b['parts'] if x['price_usd'] is None]
 result.append(dict(id=b['id'],title=titles[b['id']],title_en=b['title_en'],source_url=b['source_url'],
  source_html=b['html_file'],items=[dict(product_id='pcpp-'+pid,quantity=q) for pid,q in counts.items()],
  quoted_subtotal_vnd=subtotal,total_vnd=subtotal if not missing else None,
  missing_price_product_ids=sorted(set('pcpp-'+p for p in missing)),
  note='Tổng phần có giá chỉ là tổng tạm tính; số lượng tính theo các dòng linh kiện của bản lưu HTML.'))
for name,data in [('products.vi.json',products),('builds.vi.json',result)]:
 (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (folder/'products.vi.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['Mã','Tên tiếng Việt','Danh mục','USD','VNĐ','Có giá','Ảnh','Thông số','Nguồn'])
 for p in products:w.writerow([p['id'],p['name'],p['cat'],p['source']['price_usd'],p['price'] if p['active'] else '',p['active'],p['img'],json.dumps(p['specs'],ensure_ascii=False),p['source']['url']])
summary=dict(builds=len(result),products=len(products),images=sum(bool(p['img']) for p in products),
 priced=sum(p['active'] for p in products),missing_prices=sum(not p['active'] for p in products))
(folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(summary)
