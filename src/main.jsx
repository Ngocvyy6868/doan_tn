import Builder from './PcBuilder.jsx';
import React,{useEffect,useMemo,useState} from 'react';
import{createRoot}from'react-dom/client';
import{Search,ShoppingCart,Heart,User,ChevronRight,ChevronDown,Sparkles,ShieldCheck,Truck,Headphones,Plus,Minus,X,Check,Star,SlidersHorizontal,ArrowRight,MessageCircle,Send,Menu,Microchip,Cpu,MemoryStick,HardDrive,Box,Zap,MapPin,Pencil,Trash2}from'lucide-react';
import'./style.css';
import { ConfigProvider, Steps } from 'antd';
import 'antd/dist/reset.css';
import viVN from 'antd/locale/vi_VN';
import RegisterPage from './views/RegisterPage.jsx';
import LoginPage from './views/LoginPage.jsx';
import locations from './assets/vn-locations.json';
const AdminApp=React.lazy(()=>import('./admin.jsx'));
const apiBaseUrl=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api';

const cats=[['CPU',Cpu],['VGA',Microchip],['Mainboard',MemoryStick],['RAM',MemoryStick],['SSD',HardDrive],['Nguồn',Zap],['Case',Box]];
export const products=[
 {id:1,name:'AMD Ryzen 7 7800X3D',cat:'CPU',brand:'AMD',price:9890000,old:10990000,rate:4.9,reviews:128,badge:'-10%',img:'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?auto=format&fit=crop&w=700&q=80',description:'Bộ xử lý gaming hiệu năng cao với công nghệ AMD 3D V-Cache.',productInfo:'AMD Ryzen 7 7800X3D là bộ xử lý được tối ưu cho gaming, sử dụng kiến trúc Zen 4 và công nghệ 3D V-Cache. Sản phẩm mang lại hiệu năng cao, mức tiêu thụ điện hợp lý và hỗ trợ nền tảng AM5 hiện đại.',attributes:[{name:'Số nhân',value:'8',unit:'nhân'},{name:'Số luồng',value:'16',unit:'luồng'},{name:'Xung nhịp tối đa',value:'5.0',unit:'GHz'},{name:'Bộ nhớ đệm',value:'96',unit:'MB'},{name:'Socket',value:'AM5'}]},
 {id:2,name:'GeForce RTX 4070 SUPER',cat:'VGA',brand:'GIGABYTE',price:17890000,old:19590000,rate:4.8,reviews:86,badge:'BÁN CHẠY',img:'https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=700&q=80'},
 {id:3,name:'ROG STRIX B650E-F Gaming WiFi',cat:'Mainboard',brand:'ASUS',price:6590000,old:7290000,rate:4.7,reviews:54,badge:'-9%',img:'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=700&q=80'},
 {id:4,name:'Corsair Vengeance RGB 32GB DDR5',cat:'RAM',brand:'CORSAIR',price:2890000,old:3290000,rate:4.9,reviews:102,badge:'MỚI',img:'https://images.unsplash.com/photo-1562976540-1502c2145186?auto=format&fit=crop&w=700&q=80'},
 {id:5,name:'Samsung 990 PRO 2TB NVMe',cat:'SSD',brand:'SAMSUNG',price:4190000,old:4690000,rate:4.8,reviews:74,badge:'-11%',img:'https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=700&q=80'},
 {id:6,name:'Cooler Master MWE Gold 850 V2',cat:'Nguồn',brand:'COOLER MASTER',price:2490000,old:2790000,rate:4.6,reviews:39,badge:'GIÁ TỐT',img:'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=700&q=80'},
];
const money=n=>n.toLocaleString('vi-VN')+'₫';
const categorySlug=name=>encodeURIComponent(name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/\s+/g,'-'));
const readStore=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))||fallback}catch{return fallback}};
const writeStore=(key,value)=>localStorage.setItem(key,JSON.stringify(value));
const addToStoredCart=product=>{const cart=readStore('techzone_cart',[]),found=cart.find(x=>x.id===product.id),limit=Number.isFinite(product.stock)?product.stock:99;const next=found?cart.map(x=>x.id===product.id?{...x,q:Math.min(x.q+1,limit)}:x):[...cart,{...product,q:1}];writeStore('techzone_cart',next);return next};
const doLogout=()=>fetch(`${apiBaseUrl}/auth/logout/`,{method:'POST',credentials:'include'}).catch(()=>{}).finally(()=>{localStorage.removeItem('techzone_user');location.href='/'});

function App(){
 const[catalog]=useState(()=>{try{return JSON.parse(localStorage.getItem('techzone_products'))||products}catch{return products}});
 const[account]=useState(()=>{try{return JSON.parse(localStorage.getItem('techzone_user'))}catch{return null}});
 const[accountMenu,setAccountMenu]=useState(false);
 const[query,setQuery]=useState(''),[active,setActive]=useState('Tất cả'),[cart,setCart]=useState(()=>readStore('techzone_cart',[])),[wish,setWish]=useState([]),[drawer,setDrawer]=useState(false),[chat,setChat]=useState(false),[builder,setBuilder]=useState(false),[msg,setMsg]=useState('');
 useEffect(()=>writeStore('techzone_cart',cart),[cart]);
 const filtered=useMemo(()=>catalog.filter(p=>p.active!==false&&(active==='Tất cả'||p.cat===active)&&p.name.toLowerCase().includes(query.toLowerCase())),[query,active,catalog]);
 const add=p=>{setCart(c=>{const f=c.find(x=>x.id===p.id),limit=Number.isFinite(p.stock)?p.stock:99;return f?c.map(x=>x.id===p.id?{...x,q:Math.min(x.q+1,limit)}:x):[...c,{...p,q:1}]});setDrawer(true)};
 const count=cart.reduce((s,x)=>s+x.q,0),total=cart.reduce((s,x)=>s+x.price*x.q,0);
 const quantity=(id,d)=>setCart(c=>c.map(x=>x.id===id?{...x,q:x.q+d}:x).filter(x=>x.q>0));
 const toggleWish=id=>setWish(w=>w.includes(id)?w.filter(x=>x!==id):[...w,id]);
 return <>
  <div className="topbar"><span>TechZone • Giá tốt mỗi ngày</span><div>Hotline: <b>1900 6868</b><i/> Tra cứu đơn hàng <i/> Hệ thống cửa hàng</div></div>
  <header><a className="logo" href="#"><span>TZ</span><b>TECHZONE<small>BUILD YOUR POWER</small></b></a>
   <div className="search"><Search size={20}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Bạn cần tìm linh kiện gì?"/><button>Tìm kiếm</button></div>
   <div className="actions"><div className="account-menu-wrap"><button onClick={()=>account?setAccountMenu(value=>!value):location.href='/login'}><User/><span>{account?.full_name||'Tài khoản'}<small>{account?'Đã đăng nhập':'Đăng nhập'}</small></span></button>{account&&accountMenu&&<div className="account-dropdown"><a href="/profile"><User/>Thông tin cơ bản</a><a href="/addresses"><MapPin/>Sổ địa chỉ</a><a href="/orders"><ShoppingCart/>Đơn hàng của tôi</a><button type="button" className="logout" onClick={doLogout}>Thoát</button></div>}</div><button onClick={()=>setDrawer(true)}><ShoppingCart/><span>Giỏ hàng<small>{count} sản phẩm</small></span>{count>0&&<em>{count}</em>}</button><button className="hamb"><Menu/></button></div>
  </header>
  <nav><button><Menu size={18}/> DANH MỤC SẢN PHẨM</button>{['PC BUILDER','PC GAMING','LAPTOP','MÀN HÌNH','PHỤ KIỆN','TIN CÔNG NGHỆ'].map(x=><a key={x} onClick={()=>x==='PC BUILDER'&&setBuilder(true)}>{x}{x==='PC BUILDER'&&<b>AI</b>}</a>)}</nav>
  <main>
   <section className="home-hero"><aside className="hero-catalog"><h2><Menu/> Danh mục sản phẩm</h2>{cats.map(([name,Icon])=><a key={name} href={`/collections/${categorySlug(name)}`}><Icon/><span>{name}</span><ChevronRight/></a>)}<a href="/collections/all"><Box/><span>Xem tất cả sản phẩm</span><ChevronRight/></a></aside><div className="hero-showcase"><div className="hero-main"><img src="/pc-hero.png" alt="Build PC cùng TechZone"/><div className="hero-main-copy"><span><Sparkles/> TƯ VẤN CẤU HÌNH BẰNG AI</span><h1>BUILD PC<br/><strong>KHÔNG CÒN KHÓ</strong></h1><p>Chọn đúng linh kiện, tối ưu hiệu năng<br/>và kiểm tra tương thích trong vài giây.</p><button onClick={()=>setBuilder(true)}>BUILD PC NGAY <ArrowRight/></button></div></div><div className="hero-deals"><article><div><span>COMBO TIẾT KIỆM</span><h3>CPU + Mainboard</h3><p>Hiệu năng mạnh mẽ, giá tốt hơn khi mua cùng.</p><button onClick={()=>location.href='/collections/cpu'}>Xem combo <ChevronRight/></button></div><img src={products[0].img} alt="CPU combo"/></article><article><div><span>PC GAMING</span><h3>Chiến game cực đỉnh</h3><p>Linh kiện cân mọi tựa game phổ biến.</p><button onClick={()=>setBuilder(true)}>Build cùng AI <ChevronRight/></button></div><img src={products[1].img} alt="Gaming graphics card"/></article><article className="deal-accent"><div><span>FLASH SALE</span><h3>SSD tốc độ cao</h3><p>Giảm đến 11% trong hôm nay.</p><button onClick={()=>location.href='/collections/ssd'}>Mua ngay <ChevronRight/></button></div><img src={products[4].img} alt="SSD sale"/></article></div></div></section>
   <section className="perks"><div><Truck/><span><b>Giao hàng siêu tốc</b><small>Nội thành trong 2 giờ</small></span></div><div><ShieldCheck/><span><b>Bảo hành chính hãng</b><small>Đổi mới trong 30 ngày</small></span></div><div><Headphones/><span><b>Hỗ trợ kỹ thuật 24/7</b><small>Đội ngũ chuyên gia tận tâm</small></span></div><div><Zap/><span><b>Lắp ráp miễn phí</b><small>Đi dây & tối ưu hệ thống</small></span></div></section>
   <section className="categories"><div className="section-title"><div><span>KHÁM PHÁ</span><h2>Danh mục nổi bật</h2></div><a href="/collections/all">Xem tất cả <ChevronRight/></a></div><div className="cat-grid">{cats.map(([n,I])=><a key={n} href={`/collections/${categorySlug(n)}`}><I/><b>{n}</b><small>Khám phá ngay</small></a>)}</div></section>
   <section className="shop"><div className="section-title"><div><span>ƯU ĐÃI HÔM NAY</span><h2>Sản phẩm nổi bật</h2></div><div className="tabs">{['Tất cả','CPU','VGA','Mainboard','RAM'].map(x=><button className={active===x?'on':''} onClick={()=>setActive(x)}>{x}</button>)}</div></div>
    <div className="product-grid">{filtered.length?filtered.map(p=><article key={p.id} className="product-card-link" role="link" tabIndex={0} onClick={()=>location.href=`/product/${p.id}`} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();location.href=`/product/${p.id}`}}}><a className="visual product-link" href={`/product/${p.id}`} aria-label={`Xem chi tiết ${p.name}`}><img src={p.img}/><span className={p.badge==='BÁN CHẠY'?'hot':''}>{p.badge}</span></a><button className={`wish-button ${wish.includes(p.id)?'liked':''}`} onClick={e=>{e.stopPropagation();toggleWish(p.id)}}><Heart fill={wish.includes(p.id)?'currentColor':'none'}/></button><small>{p.brand} • {p.cat}</small><h3><a className="product-name" href={`/product/${p.id}`}>{p.name}</a></h3><div className="rating"><Star fill="currentColor"/> {p.rate} <span>({p.reviews} đánh giá)</span></div><div className="price"><b>{money(p.price)}</b><del>{money(p.old)}</del></div><button className="add" onClick={e=>{e.stopPropagation();add(p)}}><ShoppingCart/> Thêm vào giỏ</button></article>):<div className="empty">Không tìm thấy sản phẩm phù hợp.</div>}</div>
   </section>
   <section className="build-cta"><div><span>PC BUILDER THÔNG MINH</span><h2>Cấu hình chuẩn. Hiệu năng đỉnh.</h2><p>Chọn linh kiện theo nhu cầu và ngân sách. Hệ thống tự động cảnh báo xung đột phần cứng.</p><button className="primary" onClick={()=>setBuilder(true)}>BẮT ĐẦU BUILD PC <ArrowRight/></button></div><div className="build-stat"><div><Check/><b>100%</b><span>Kiểm tra tương thích</span></div><div><Sparkles/><b>AI</b><span>Tư vấn theo nhu cầu</span></div></div></section>
  </main>
  <footer><a className="logo"><span>TZ</span><b>TECHZONE<small>BUILD YOUR POWER</small></b></a><p>Hệ sinh thái linh kiện và giải pháp PC toàn diện.</p><div>© 2026 TechZone. All rights reserved.</div></footer>
  <button className="chat-fab" onClick={()=>setChat(!chat)}><MessageCircle/><span>Hỏi AI</span></button>
  {chat&&<div className="chat"><div className="chat-head"><span><Sparkles/> TechZone AI <small>Trực tuyến</small></span><button onClick={()=>setChat(false)}><X/></button></div><div className="chat-body"><div className="bot">Chào bạn! Mình có thể tư vấn cấu hình, kiểm tra tương thích và tìm linh kiện theo ngân sách. Bạn đang cần build PC để làm gì?</div><div className="suggest"><button>Gaming 2K</button><button>Đồ họa 3D</button><button>Ngân sách 25 triệu</button></div></div><div className="chat-input"><input value={msg} onChange={e=>setMsg(e.target.value)} placeholder="Nhập câu hỏi..."/><button onClick={()=>setMsg('')}><Send/></button></div></div>}
  {drawer&&<><div className="shade" onClick={()=>setDrawer(false)}/><aside className="drawer"><div className="drawer-head"><h2>Giỏ hàng <span>({count})</span></h2><button onClick={()=>setDrawer(false)}><X/></button></div><div className="cart-list">{cart.length?cart.map(x=><div className="cart-item" key={x.id}><img src={x.img}/><div><b>{x.name}</b><strong>{money(x.price)}</strong><div className="qty"><button onClick={()=>quantity(x.id,-1)}><Minus/></button><span>{x.q}</span><button onClick={()=>quantity(x.id,1)}><Plus/></button></div></div></div>):<div className="cart-empty"><ShoppingCart/><h3>Giỏ hàng đang trống</h3><p>Khám phá linh kiện phù hợp cho bộ PC của bạn.</p></div>}</div>{cart.length>0&&<div className="checkout"><div><span>Tạm tính</span><b>{money(total)}</b></div><button onClick={()=>location.href='/checkout'}>TIẾN HÀNH THANH TOÁN <ArrowRight/></button><small><ShieldCheck/> Thanh toán an toàn & bảo mật</small></div>}</aside></>}
  {builder&&<Builder close={()=>setBuilder(false)} add={add} products={catalog}/>} 
 </>
}
function CollectionPage(){
 const slug=decodeURIComponent(location.pathname.split('/').filter(Boolean)[1]||'all');
 const category=slug==='all'?'Tất cả':cats.map(([name])=>name).find(name=>categorySlug(name)===slug);
 const catalog=readStore('techzone_products',products).filter(p=>p.active!==false&&(category==='Tất cả'||p.cat===category));
 const[added,setAdded]=useState([]);
 if(!category)return <><ConsumerHeader/><main className="collection-page"><div className="checkout-empty"><Box/><h2>Không tìm thấy danh mục</h2><a href="/">Về trang chủ</a></div></main></>;
 const add=p=>{addToStoredCart(p);setAdded(ids=>ids.includes(p.id)?ids:[...ids,p.id])};
 return <><ConsumerHeader/><main className="collection-page"><div className="product-breadcrumb"><a href="/">Trang chủ</a><ChevronRight/><b>{category}</b></div><div className="collection-heading"><div><span>COLLECTION</span><h1>{category==='Tất cả'?'Tất cả sản phẩm':category}</h1><p>{catalog.length} sản phẩm đang hiển thị</p></div><a href="/">← Về trang chủ</a></div>{catalog.length?<div className="product-grid collection-grid">{catalog.map(p=><article key={p.id} className="product-card-link" role="link" tabIndex={0} onClick={()=>location.href=`/product/${p.id}`} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();location.href=`/product/${p.id}`}}}><a className="visual product-link" href={`/product/${p.id}`}><img src={p.img} alt={p.name}/>{p.badge&&<span className={p.badge==='BÁN CHẠY'?'hot':''}>{p.badge}</span>}</a><small>{p.brand} • {p.cat}</small><h3><a className="product-name" href={`/product/${p.id}`}>{p.name}</a></h3><div className="rating"><Star fill="currentColor"/> {p.rate||5} <span>({p.reviews||0} đánh giá)</span></div><div className="price"><b>{money(p.price)}</b>{p.old>p.price&&<del>{money(p.old)}</del>}</div><button className={`add ${added.includes(p.id)?'added':''}`} onClick={e=>{e.stopPropagation();add(p)}}>{added.includes(p.id)?<><Check/> Đã thêm vào giỏ</>:<><ShoppingCart/> Thêm vào giỏ</>}</button></article>)}</div>:<div className="collection-empty"><Box/><h2>Danh mục chưa có sản phẩm</h2><p>Sản phẩm mới sẽ sớm được cập nhật.</p></div>}</main><footer><a className="logo" href="/"><span>TZ</span><b>TECHZONE<small>BUILD YOUR POWER</small></b></a><p>Hệ sinh thái linh kiện và giải pháp PC toàn diện.</p></footer></>;
}
function ProductDetailsPage(){
 const[added,setAdded]=useState(false);
 const[contentTab,setContentTab]=useState('info');
 const catalog=(()=>{try{return JSON.parse(localStorage.getItem('techzone_products'))||products}catch{return products}})();
 const id=decodeURIComponent(location.pathname.split('/').filter(Boolean)[1]||'');
 const product=catalog.find(p=>String(p.id)===id);
 if(!product)return <><ConsumerHeader/><main className="product-page"><div className="product-not-found"><h1>Không tìm thấy sản phẩm</h1><p>Sản phẩm có thể đã bị xóa hoặc đường dẫn không còn hợp lệ.</p><a href="/">← Quay lại cửa hàng</a></div></main></>;
 const attributes=product.attributes||[];
 const unavailable=product.active===false||product.stock<=0;
 const add=()=>{if(unavailable)return;addToStoredCart(product);setAdded(true)};
 const buyNow=()=>{if(unavailable)return;sessionStorage.setItem('techzone_buy_now',JSON.stringify([{...product,q:1}]));sessionStorage.removeItem('techzone_buy_now_key');location.href='/checkout?buyNow=1'};
 return <><ConsumerHeader/><main className="product-page"><div className="product-breadcrumb"><a href="/">Trang chủ</a><ChevronRight/><span>{product.cat}</span><ChevronRight/><b>{product.name}</b></div><article className="product-detail"><div className="detail-summary"><div className="detail-image"><img src={product.img} alt={product.name}/>{product.badge&&<span>{product.badge}</span>}</div><div><small>{product.brand} • {product.cat} {product.sku&&`• ${product.sku}`}</small><h1>{product.name}</h1><div className="rating"><Star fill="currentColor"/> {product.rate||5} <span>({product.reviews||0} đánh giá)</span></div><p>{product.description||'Sản phẩm chính hãng, được bảo hành và hỗ trợ kỹ thuật tại TechZone.'}</p><div className="stock-state"><Check/> {product.stock===0?'Tạm hết hàng':`Còn hàng${Number.isFinite(product.stock)?` (${product.stock} sản phẩm)`:''}`}</div><div className="detail-price">{money(product.price)} {product.old>product.price&&<del>{money(product.old)}</del>}</div><div className="detail-purchase-actions"><button type="button" className="detail-add" disabled={unavailable} onClick={add}>{added?<><Check/> Đã thêm vào giỏ</>:<><ShoppingCart/> Thêm vào giỏ hàng</>}</button><button type="button" className="detail-buy-now" disabled={unavailable} onClick={buyNow}>Mua ngay</button></div><div className="detail-policies"><span><ShieldCheck/> Bảo hành chính hãng</span><span><Truck/> Giao hàng nhanh</span><span><Headphones/> Hỗ trợ kỹ thuật</span></div></div></div><section className="technical-specs"><div className="product-content-tabs" role="tablist"><button role="tab" aria-selected={contentTab==='info'} className={contentTab==='info'?'active':''} onClick={()=>setContentTab('info')}>Thông tin sản phẩm</button><button role="tab" aria-selected={contentTab==='specs'} className={contentTab==='specs'?'active':''} onClick={()=>setContentTab('specs')}>Thông số kỹ thuật</button></div>{contentTab==='info'?<div className="product-info-content">{product.productInfo?<p>{product.productInfo}</p>:<p>Thông tin sản phẩm đang được cập nhật.</p>}</div>:attributes.length?<dl>{attributes.map((a,i)=><div key={`${a.name}-${i}`}><dt>{a.name}</dt><dd>{a.value}{a.unit?` ${a.unit}`:''}</dd></div>)}</dl>:<p className="no-specs">Thông số kỹ thuật đang được cập nhật.</p>}</section></article></main><footer><a className="logo" href="/"><span>TZ</span><b>TECHZONE<small>BUILD YOUR POWER</small></b></a><p>Hệ sinh thái linh kiện và giải pháp PC toàn diện.</p></footer></>;
}
function CheckoutPage(){
 const buyNow=new URLSearchParams(location.search).get('buyNow')==='1';
 const checkoutKey=buyNow?'techzone_buy_now_key':'techzone_checkout_key';
 const saveCheckoutCart=next=>buyNow?sessionStorage.setItem('techzone_buy_now',JSON.stringify(next)):writeStore('techzone_cart',next);
 const[cart,setCart]=useState(()=>{if(!buyNow)return readStore('techzone_cart',[]);try{return JSON.parse(sessionStorage.getItem('techzone_buy_now'))||[]}catch{return []}}),[payment,setPayment]=useState('COD'),[shipping,setShipping]=useState('standard'),[submitting,setSubmitting]=useState(false),[error,setError]=useState('');
 const[account]=useState(()=>{try{return JSON.parse(localStorage.getItem('techzone_user'))}catch{return null}});
 const[savedAddresses,setSavedAddresses]=useState([]),[selectedAddressId,setSelectedAddressId]=useState('manual');
 const[customer,setCustomer]=useState({name:'',phone:'',provinceCode:'',provinceName:'',wardCode:'',wardName:'',address:''});
 useEffect(()=>{if(!account)return;fetch(`${apiBaseUrl}/addresses/`,{credentials:'include'}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{const results=data.results||[];setSavedAddresses(results);const def=results.find(a=>a.isDefault)||results[0];if(def)setSelectedAddressId(def.id)}).catch(()=>{})},[account]);
 useEffect(()=>{if(selectedAddressId==='manual')return;const selected=savedAddresses.find(a=>a.id===selectedAddressId);if(selected)setCustomer({name:selected.fullName,phone:selected.phone,provinceCode:selected.provinceCode,provinceName:selected.provinceName,wardCode:selected.wardCode,wardName:selected.wardName,address:selected.detail})},[selectedAddressId,savedAddresses]);
 const subtotal=cart.reduce((s,x)=>s+x.price*x.q,0),shippingFee=shipping==='express'?60000:subtotal>=20000000?0:30000,total=subtotal+shippingFee;
 const changeQty=(id,delta)=>{const next=cart.map(x=>x.id===id?{...x,q:Math.max(0,Math.min(x.q+delta,Number.isFinite(x.stock)?x.stock:99))}:x).filter(x=>x.q>0);setCart(next);saveCheckoutCart(next)};
 const placeOrder=async e=>{e.preventDefault();setError('');if(!cart.length)return setError('Giỏ hàng đang trống.');if(!customer.name.trim()||!/^0\d{9}$/.test(customer.phone)||!customer.provinceCode||!customer.wardCode||!customer.address.trim())return setError('Vui lòng nhập đầy đủ thông tin nhận hàng và số điện thoại hợp lệ.');const catalog=readStore('techzone_products',products);const invalid=cart.find(item=>{const current=catalog.find(p=>p.id===item.id);return current?.active===false||(Number.isFinite(current?.stock)&&item.q>current.stock)});if(invalid)return setError(`${invalid.name} không còn đủ tồn kho. Vui lòng cập nhật giỏ hàng.`);setSubmitting(true);const key=sessionStorage.getItem(checkoutKey)||crypto.randomUUID();sessionStorage.setItem(checkoutKey,key);const orders=readStore('techzone_orders',[]),existing=orders.find(o=>o.idempotencyKey===key);if(existing){location.href=`/orders/${existing.code}`;return}const now=new Date().toISOString(),code=`TZ${Date.now().toString().slice(-10)}`;const recipient={name:customer.name.trim(),phone:customer.phone,province:`${customer.wardName}, ${customer.provinceName}`,address:customer.address.trim()};const order={id:crypto.randomUUID(),code,idempotencyKey:key,createdAt:now,status:'CONFIRMED',paymentStatus:payment==='SANDBOX'?'PAID':'UNPAID',paymentMethod:payment,shippingMethod:shipping,address:recipient,items:cart.map(x=>({productId:x.id,sku:x.sku||`TZ-${x.id}`,name:x.name,img:x.img,price:x.price,quantity:x.q,total:x.price*x.q})),totals:{subtotal,discount:0,shipping:shippingFee,grandTotal:total},timeline:[{status:'CONFIRMED',label:'Đơn hàng đã được xác nhận',at:now},{status:'PENDING',label:'Đang chờ đóng gói',at:null}]};try{const response=await fetch(`${apiBaseUrl}/orders/`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({...order,payment_method:order.paymentMethod,payment_status:order.paymentStatus,shipping_method:order.shippingMethod})});if(!response.ok)throw new Error()}catch{setSubmitting(false);return setError('Không thể lưu đơn hàng vào máy chủ. Vui lòng thử lại.')}writeStore('techzone_orders',[order,...orders]);saveCheckoutCart([]);sessionStorage.removeItem(checkoutKey);location.href=`/orders/${code}`};
 return <><ConsumerHeader/><main className="checkout-page"><div className="checkout-heading"><a href="/">← Tiếp tục mua hàng</a><h1>Thanh toán</h1><p>Kiểm tra sản phẩm và hoàn tất thông tin đặt hàng.</p></div>{cart.length?<form className="checkout-layout" onSubmit={placeOrder}><div className="checkout-form"><section><h2>1. Thông tin nhận hàng</h2>{account&&<a href="/addresses" className="manage-address-link">Quản lý sổ địa chỉ</a>}{savedAddresses.length>0&&<div className="saved-address-list">{savedAddresses.map(a=><label key={a.id} className={`option-card ${selectedAddressId===a.id?'selected':''}`}><input type="radio" checked={selectedAddressId===a.id} onChange={()=>setSelectedAddressId(a.id)}/><MapPin/><span><b>{a.fullName} • {a.phone}</b><small>{a.detail}, {a.wardName}, {a.provinceName}</small></span>{a.isDefault&&<strong>Mặc định</strong>}</label>)}<label className={`option-card ${selectedAddressId==='manual'?'selected':''}`}><input type="radio" checked={selectedAddressId==='manual'} onChange={()=>setSelectedAddressId('manual')}/><Plus/><span><b>Nhập địa chỉ khác</b></span></label></div>}{selectedAddressId==='manual'&&<><div className="field-grid"><label>Họ và tên<input value={customer.name} onChange={e=>setCustomer({...customer,name:e.target.value})} placeholder="Nguyễn Văn A"/></label><label>Số điện thoại<input value={customer.phone} onChange={e=>setCustomer({...customer,phone:e.target.value})} placeholder="0901234567"/></label></div><LocationPicker provinceCode={customer.provinceCode} provinceName={customer.provinceName} wardCode={customer.wardCode} wardName={customer.wardName} onSelect={(pc,pn,wc,wn)=>setCustomer(c=>({...c,provinceCode:pc,provinceName:pn,wardCode:wc,wardName:wn}))}/><label>Địa chỉ chi tiết<textarea value={customer.address} onChange={e=>setCustomer({...customer,address:e.target.value})} placeholder="Số nhà, đường, phường/xã, quận/huyện"/></label></>}</section><section><h2>2. Phương thức giao hàng</h2><label className={`option-card ${shipping==='standard'?'selected':''}`}><input type="radio" checked={shipping==='standard'} onChange={()=>setShipping('standard')}/><Truck/><span><b>Giao hàng tiêu chuẩn</b><small>2–4 ngày làm việc</small></span><strong>{subtotal>=20000000?'Miễn phí':money(30000)}</strong></label><label className={`option-card ${shipping==='express'?'selected':''}`}><input type="radio" checked={shipping==='express'} onChange={()=>setShipping('express')}/><Zap/><span><b>Giao hàng nhanh</b><small>Trong 24 giờ</small></span><strong>{money(60000)}</strong></label></section><section><h2>3. Phương thức thanh toán</h2><label className={`option-card ${payment==='COD'?'selected':''}`}><input type="radio" checked={payment==='COD'} onChange={()=>setPayment('COD')}/><Box/><span><b>Thanh toán khi nhận hàng (COD)</b><small>Thanh toán cho nhân viên giao hàng</small></span></label><label className={`option-card ${payment==='SANDBOX'?'selected':''}`}><input type="radio" checked={payment==='SANDBOX'} onChange={()=>setPayment('SANDBOX')}/><ShieldCheck/><span><b>Thanh toán điện tử Sandbox</b><small>Mô phỏng giao dịch thành công, không trừ tiền thật</small></span></label></section></div><aside className="order-summary"><h2>Đơn hàng ({cart.reduce((s,x)=>s+x.q,0)} sản phẩm)</h2><div className="checkout-items">{cart.map(x=><div key={x.id}><img src={x.img}/><span><b>{x.name}</b><small>{money(x.price)}</small><span className="checkout-qty"><button type="button" onClick={()=>changeQty(x.id,-1)}><Minus/></button>{x.q}<button type="button" onClick={()=>changeQty(x.id,1)}><Plus/></button></span></span><strong>{money(x.price*x.q)}</strong></div>)}</div><div className="total-lines"><span>Tạm tính <b>{money(subtotal)}</b></span><span>Giảm giá <b>0₫</b></span><span>Phí giao hàng <b>{shippingFee?money(shippingFee):'Miễn phí'}</b></span><strong>Tổng cộng <b>{money(total)}</b></strong></div>{error&&<div className="checkout-error">{error}</div>}<button className="place-order" disabled={submitting}>{submitting?'ĐANG TẠO ĐƠN...':payment==='COD'?'ĐẶT HÀNG COD':'THANH TOÁN SANDBOX'}</button><small className="secure-note"><ShieldCheck/> Giá đã gồm VAT. Đơn hàng chỉ được tạo một lần.</small></aside></form>:<div className="checkout-empty"><ShoppingCart/><h2>Giỏ hàng đang trống</h2><a href="/">Quay lại mua sắm</a></div>}</main></>}
function useCustomerOrders(code){
 const [orders,setOrders]=useState(()=>readStore('techzone_orders',[]));
 const [syncError,setSyncError]=useState(false);
 useEffect(()=>{
  let disposed=false,inFlight=false;
  const controller=new AbortController();
  const sync=async()=>{
   if(inFlight||document.visibilityState==='hidden')return;
   inFlight=true;
   try{
    const stored=readStore('techzone_orders',[]);
    const targets=code?stored.filter(order=>order.code===code):stored;
    const results=await Promise.allSettled(targets.map(async order=>{
     const response=await fetch(`${apiBaseUrl}/orders/status/`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:order.code,phone:order.address.phone}),signal:controller.signal});
     if(!response.ok)throw new Error();
     return response.json();
    }));
    if(disposed)return;
    const updates=results.filter(result=>result.status==='fulfilled').map(result=>result.value);
    const next=readStore('techzone_orders',[]).map(order=>{const update=updates.find(item=>item.code===order.code);return update?{...order,status:update.status,paymentStatus:update.paymentStatus}:order});
    writeStore('techzone_orders',next);
    setOrders(next);
    setSyncError(results.some(result=>result.status==='rejected'));
   }catch{if(!disposed)setSyncError(true)}
   finally{inFlight=false}
  };
  sync();
  const timer=setInterval(sync,5000);
  window.addEventListener('focus',sync);
  document.addEventListener('visibilitychange',sync);
  return()=>{disposed=true;controller.abort();clearInterval(timer);window.removeEventListener('focus',sync);document.removeEventListener('visibilitychange',sync)};
 },[code]);
 return {orders,syncError};
}
function OrdersPage(){const {orders,syncError}=useCustomerOrders();return <><ConsumerHeader/><main className="orders-page"><div className="checkout-heading"><a href="/">← Về cửa hàng</a><h1>Đơn hàng của tôi</h1><p>Theo dõi trạng thái thanh toán và giao nhận.</p></div>{syncError&&<p className="checkout-error" role="status">Chưa thể đồng bộ trạng thái mới nhất. Hệ thống sẽ tự thử lại.</p>}{orders.length?<div className="order-list">{orders.map(o=><a href={`/orders/${o.code}`} key={o.id}><div><b>#{o.code}</b><small>{new Date(o.createdAt).toLocaleString('vi-VN')}</small></div><span>{o.items.length} sản phẩm</span><strong>{money(o.totals.grandTotal)}</strong><em>{orderLabel(o.status)}</em><ChevronRight/></a>)}</div>:<div className="checkout-empty"><Box/><h2>Chưa có đơn hàng</h2><a href="/">Bắt đầu mua sắm</a></div>}</main></>}
const orderLabel=status=>({PENDING_PAYMENT:'Chờ thanh toán',CONFIRMED:'Đã xác nhận',PACKING:'Đang đóng gói',READY_FOR_PICKUP:'Chờ lấy hàng',DELIVERING:'Đang giao',DELIVERED:'Hoàn tất',CANCELLED:'Đã hủy'})[status]||status;
function OrderProgress({order}){
 const steps=[{key:'CONFIRMED',title:'Đã xác nhận',description:'Đơn hàng đã được tiếp nhận.'},{key:'PACKING',title:'Đang đóng gói',description:'Sản phẩm đang được chuẩn bị.'},{key:'DELIVERING',title:'Đang giao hàng',description:'Đơn hàng đang trên đường đến bạn.'},{key:'DELIVERED',title:'Hoàn tất',description:'Đơn hàng đã giao thành công.'}];
 const current=steps.findIndex(step=>step.key===order.status);
 if(order.status==='CANCELLED')return <p role="status">Đơn hàng đã bị hủy.</p>;
 return <Steps className="consumer-order-steps" direction="vertical" current={current} items={steps.map((step,index)=>({...step,status:order.status==='DELIVERED'||index<current?'finish':index===current?'process':'wait'}))}/>;
}function OrderDetailPage(){const code=decodeURIComponent(location.pathname.split('/').filter(Boolean)[1]||''), {orders,syncError}=useCustomerOrders(code),order=orders.find(o=>o.code===code);if(!order)return <><ConsumerHeader/><main className="orders-page"><div className="checkout-empty"><WarningIcon/><h2>Không tìm thấy đơn hàng</h2><a href="/orders">Xem lịch sử đơn</a></div></main></>;return <><ConsumerHeader/><main className="orders-page"><div className="checkout-heading"><a href="/orders">← Danh sách đơn hàng</a><h1>Đơn hàng #{order.code}</h1><p>Đặt lúc {new Date(order.createdAt).toLocaleString('vi-VN')}</p></div><div className="order-detail-grid"><div><section className="order-status"><h2>{orderLabel(order.status)}</h2><p>{order.paymentMethod==='COD'?'Thanh toán khi nhận hàng':'Thanh toán điện tử Sandbox'} • {order.paymentStatus==='PAID'?'Đã thanh toán':'Chưa thanh toán'}</p>{syncError&&<p className="checkout-error" role="status">Chưa thể đồng bộ trạng thái mới nhất. Hệ thống sẽ tự thử lại.</p>}<OrderProgress order={order}/></section><section className="ordered-products"><h2>Sản phẩm</h2>{order.items.map(x=><div key={x.sku}><img src={x.img}/><span><b>{x.name}</b><small>SKU: {x.sku} • SL: {x.quantity}</small></span><strong>{money(x.total)}</strong></div>)}</section></div><aside className="order-meta"><section><h3>Địa chỉ nhận hàng</h3><b>{order.address.name}</b><p>{order.address.phone}<br/>{order.address.address}, {order.address.province}</p></section><section><h3>Thanh toán</h3><span>Tạm tính <b>{money(order.totals.subtotal)}</b></span><span>Phí giao hàng <b>{order.totals.shipping?money(order.totals.shipping):'Miễn phí'}</b></span><strong>Tổng cộng <b>{money(order.totals.grandTotal)}</b></strong></section></aside></div></main></>}
function WarningIcon(){return <span className="warning-icon">!</span>}
function LocationPicker({provinceCode,provinceName,wardCode,wardName,onSelect}){
 const[open,setOpen]=useState(false),[activeProvince,setActiveProvince]=useState(provinceCode||''),[pq,setPq]=useState(''),[wq,setWq]=useState('');
 const wards=locations.wardsByProvince[activeProvince]||[];
 const filteredProvinces=locations.provinces.filter(p=>p.name.toLowerCase().includes(pq.toLowerCase()));
 const filteredWards=wards.filter(w=>w.name.toLowerCase().includes(wq.toLowerCase()));
 const pick=(province,ward)=>{onSelect(province.code,province.name,ward.code,ward.name);setOpen(false);setPq('');setWq('')};
 return <div className="field-float location-field"><label>Tỉnh/Thành phố, Phường/Xã</label>
  <button type="button" className="field-control location-trigger" onClick={()=>{setActiveProvince(provinceCode||activeProvince);setOpen(o=>!o)}}><span className={provinceName?'':'placeholder'}>{provinceName?`${provinceName}, ${wardName||'Chọn phường/xã'}`:'Chọn Tỉnh/Thành phố, Phường/Xã'}</span><ChevronDown/></button>
  {open&&<><div className="picker-shade" onClick={()=>setOpen(false)}/><div className="location-panel">
   <div className="location-col"><div className="location-search"><Search/><input value={pq} onChange={e=>setPq(e.target.value)} placeholder="Tìm tỉnh/thành phố"/></div><div className="location-list">{filteredProvinces.map(p=><button type="button" key={p.code} className={activeProvince===p.code?'active':''} onClick={()=>setActiveProvince(p.code)}>{p.name}</button>)}</div></div>
   <div className="location-col"><div className="location-search"><Search/><input value={wq} onChange={e=>setWq(e.target.value)} placeholder="Tìm phường/xã"/></div><div className="location-list">{!activeProvince?<div className="location-empty">Chọn tỉnh/thành phố trước.</div>:filteredWards.length?filteredWards.map(w=><button type="button" key={w.code} className={wardCode===w.code?'active':''} onClick={()=>pick(locations.provinces.find(p=>p.code===activeProvince),w)}>{w.name}</button>):<div className="location-empty">Không tìm thấy phường/xã.</div>}</div></div>
  </div></>}
 </div>
}
function AddressFormModal({initial,onClose,onSave}){
 const[values,setValues]=useState(()=>initial||{fullName:'',phone:'',provinceCode:'',provinceName:'',wardCode:'',wardName:'',detail:'',isDefault:false});
 const[error,setError]=useState('');
 const set=(key,v)=>setValues(s=>({...s,[key]:v}));
 const submit=e=>{e.preventDefault();if(!values.fullName.trim()||!/^0\d{9}$/.test(values.phone)||!values.provinceCode||!values.wardCode||!values.detail.trim())return setError('Vui lòng nhập đầy đủ thông tin và số điện thoại hợp lệ.');onSave(values)};
 return <div className="modal-wrap"><div className="address-modal">
  <div className="address-modal-head"><h2>{initial?'Chỉnh sửa địa chỉ':'Thêm địa chỉ mới'}</h2><button type="button" onClick={onClose}><X/></button></div>
  <form className="address-form" onSubmit={submit}>
   <div className="field-grid">
    <div className="field-float"><label>Họ và tên</label><input value={values.fullName} onChange={e=>set('fullName',e.target.value)} placeholder="Nguyễn Văn A"/></div>
    <div className="field-float"><label>Số điện thoại</label><input value={values.phone} onChange={e=>set('phone',e.target.value)} placeholder="0901234567"/></div>
   </div>
   <LocationPicker provinceCode={values.provinceCode} provinceName={values.provinceName} wardCode={values.wardCode} wardName={values.wardName} onSelect={(pc,pn,wc,wn)=>setValues(s=>({...s,provinceCode:pc,provinceName:pn,wardCode:wc,wardName:wn}))}/>
   <div className="field-float"><label>Tên đường, tòa nhà, số nhà</label><textarea value={values.detail} onChange={e=>set('detail',e.target.value)} placeholder="CITD, Tầng 1 tòa E, số 07 – 09 đường Nguyễn Bỉnh Khiêm, phường Bến Nghé"/></div>
   <label className="address-default-check"><input type="checkbox" checked={values.isDefault} onChange={e=>set('isDefault',e.target.checked)}/> Đặt làm địa chỉ mặc định</label>
   {error&&<div className="checkout-error">{error}</div>}
   <div className="address-modal-actions"><button type="button" className="ghost-btn" onClick={onClose}>Hủy</button><button type="submit" className="primary-btn">Lưu địa chỉ</button></div>
  </form>
 </div></div>
}
function ProfilePage(){
 const[account]=useState(()=>{try{return JSON.parse(localStorage.getItem('techzone_user'))}catch{return null}});
 useEffect(()=>{if(!account)location.href='/login'},[account]);
 const[form,setForm]=useState({fullName:'',email:'',phone:'',avatarUrl:''});
 const[original,setOriginal]=useState(null);
 const[currentPassword,setCurrentPassword]=useState('');
 const[loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[error,setError]=useState(''),[success,setSuccess]=useState('');
 const load=()=>fetch(`${apiBaseUrl}/account/profile/`,{credentials:'include'}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{const u=data.user;setForm({fullName:u.full_name,email:u.email,phone:u.phone,avatarUrl:u.avatar_url||''});setOriginal(u)}).catch(()=>setError('Không thể tải thông tin tài khoản.')).finally(()=>setLoading(false));
 useEffect(()=>{if(account)load()},[account]);
 const identityChanged=!!original&&(form.email!==original.email||form.phone!==original.phone);
 const submit=async e=>{
  e.preventDefault();setError('');setSuccess('');
  if(!form.fullName.trim())return setError('Vui lòng nhập họ và tên.');
  if(!/^0\d{9}$/.test(form.phone))return setError('Số điện thoại không hợp lệ.');
  if(!/^\S+@\S+\.\S+$/.test(form.email))return setError('Email không hợp lệ.');
  if(identityChanged&&!currentPassword)return setError('Vui lòng nhập mật khẩu hiện tại để xác nhận thay đổi email/số điện thoại.');
  setSaving(true);
  try{
   const response=await fetch(`${apiBaseUrl}/account/profile/`,{method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:form.fullName,email:form.email,phone:form.phone,avatar_url:form.avatarUrl,current_password:currentPassword})});
   const data=await response.json();
   if(!response.ok){Object.entries(data.errors||{}).forEach(()=>{});setError(data.message||'Không thể lưu thông tin.');return}
   const u=data.user;setOriginal(u);setForm({fullName:u.full_name,email:u.email,phone:u.phone,avatarUrl:u.avatar_url||''});setCurrentPassword('');
   localStorage.setItem('techzone_user',JSON.stringify(u));
   setSuccess('Đã cập nhật thông tin tài khoản.');
  }catch{setError('Không thể kết nối máy chủ. Vui lòng thử lại sau.')}finally{setSaving(false)}
 };
 if(!account)return null;
 return <><ConsumerHeader/><main className="address-page">
  <div className="checkout-heading address-page-head"><div><a href="/">← Về trang chủ</a><h1><User/> Thông tin cơ bản</h1><p>Xem và cập nhật họ tên, email, số điện thoại và ảnh đại diện.</p></div></div>
  {loading?<div className="checkout-empty"><User/><h2>Đang tải...</h2></div>:<form className="checkout-form profile-form" onSubmit={submit}><section>
   <div className="profile-avatar-row">{form.avatarUrl?<img src={form.avatarUrl} className="profile-avatar-preview" alt="Ảnh đại diện"/>:<div className="profile-avatar-placeholder"><User/></div>}<label>Ảnh đại diện (URL)<input value={form.avatarUrl} onChange={e=>setForm({...form,avatarUrl:e.target.value})} placeholder="https://..."/></label></div>
   <div className="field-grid"><label>Họ và tên<input value={form.fullName} onChange={e=>setForm({...form,fullName:e.target.value})} placeholder="Nguyễn Văn A"/></label><label>Số điện thoại<input value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})} placeholder="0901234567"/></label></div>
   <label>Email<input value={form.email} onChange={e=>setForm({...form,email:e.target.value})} placeholder="email@domain.com"/></label>
   {identityChanged&&<label>Mật khẩu hiện tại (xác nhận đổi email/số điện thoại)<input type="password" value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)} placeholder="Nhập mật khẩu để xác nhận"/></label>}
   {error&&<div className="checkout-error">{error}</div>}
   {success&&<div className="profile-success">{success}</div>}
   <button className="place-order profile-save" disabled={saving} type="submit">{saving?'ĐANG LƯU...':'LƯU THAY ĐỔI'}</button>
  </section></form>}
 </main></>
}
function AddressBookPage(){
 const[account]=useState(()=>{try{return JSON.parse(localStorage.getItem('techzone_user'))}catch{return null}});
 useEffect(()=>{if(!account)location.href='/login'},[account]);
 const[addresses,setAddresses]=useState([]),[loading,setLoading]=useState(true);
 const[modal,setModal]=useState(null),[confirmDeleteId,setConfirmDeleteId]=useState(null),[warning,setWarning]=useState('');
 const load=()=>fetch(`${apiBaseUrl}/addresses/`,{credentials:'include'}).then(r=>r.ok?r.json():Promise.reject()).then(data=>setAddresses(data.results||[])).catch(()=>setWarning('Không thể tải sổ địa chỉ. Vui lòng thử lại.')).finally(()=>setLoading(false));
 useEffect(()=>{if(account)load()},[account]);
 const save=async values=>{setWarning('');const url=values.id?`${apiBaseUrl}/addresses/${values.id}/`:`${apiBaseUrl}/addresses/`;try{const response=await fetch(url,{method:values.id?'PATCH':'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});const data=await response.json();if(!response.ok)return setWarning(data.message||'Không thể lưu địa chỉ.');setModal(null);load()}catch{setWarning('Không thể kết nối máy chủ. Vui lòng thử lại sau.')}};
 const setDefault=async id=>{setWarning('');try{const response=await fetch(`${apiBaseUrl}/addresses/${id}/`,{method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({isDefault:true})});if(!response.ok){const data=await response.json();return setWarning(data.message||'Không thể cập nhật địa chỉ mặc định.')}load()}catch{setWarning('Không thể kết nối máy chủ. Vui lòng thử lại sau.')}};
 const remove=async id=>{setWarning('');setConfirmDeleteId(null);try{const response=await fetch(`${apiBaseUrl}/addresses/${id}/`,{method:'DELETE',credentials:'include'});const data=await response.json();if(!response.ok)return setWarning(data.message||'Không thể xóa địa chỉ.');load()}catch{setWarning('Không thể kết nối máy chủ. Vui lòng thử lại sau.')}};
 if(!account)return null;
 return <><ConsumerHeader/><main className="address-page">
  <div className="checkout-heading address-page-head"><div><a href="/">← Về trang chủ</a><h1><MapPin/> Sổ địa chỉ</h1><p>Quản lý địa chỉ nhận hàng và chọn địa chỉ mặc định cho đơn hàng.</p></div><button type="button" className="primary-btn" onClick={()=>setModal('new')}><Plus/> Thêm địa chỉ mới</button></div>
  {warning&&<div className="checkout-error">{warning}</div>}
  {loading?<div className="checkout-empty"><MapPin/><h2>Đang tải sổ địa chỉ...</h2></div>:addresses.length?<div className="address-list">{addresses.map(a=><div className="address-card" key={a.id}>{a.isDefault&&<span className="address-default-badge"><Star fill="currentColor"/> Mặc định</span>}<b>{a.fullName}</b><span>{a.phone}</span><p>{a.detail}<br/>{a.wardName}, {a.provinceName}</p><div className="address-card-actions">{!a.isDefault&&<button type="button" onClick={()=>setDefault(a.id)}>Đặt làm mặc định</button>}<button type="button" onClick={()=>setModal(a)}><Pencil/> Chỉnh sửa</button>{confirmDeleteId===a.id?<span className="confirm-delete"><em>Xóa địa chỉ này?</em><button type="button" onClick={()=>remove(a.id)}>Xóa</button><button type="button" onClick={()=>setConfirmDeleteId(null)}>Hủy</button></span>:<button type="button" className="danger" onClick={()=>setConfirmDeleteId(a.id)}><Trash2/> Xóa</button>}</div></div>)}</div>:<div className="checkout-empty"><MapPin/><h2>Chưa có địa chỉ nào</h2><p>Thêm địa chỉ để thanh toán nhanh hơn ở lần mua tiếp theo.</p></div>}
 </main>{modal&&<AddressFormModal initial={modal==='new'?null:modal} onClose={()=>setModal(null)} onSave={save}/>}</>
}
function ConsumerHeader(){const count=readStore('techzone_cart',[]).reduce((s,x)=>s+x.q,0);return <><div className="topbar"><span>TechZone • Giá tốt mỗi ngày</span><div>Hotline: <b>1900 6868</b></div></div><header><a className="logo" href="/"><span>TZ</span><b>TECHZONE<small>BUILD YOUR POWER</small></b></a><div className="search"><Search size={20}/><input placeholder="Bạn cần tìm linh kiện gì?"/><button onClick={()=>location.href='/'}>Tìm kiếm</button></div><div className="actions"><a href="/orders" className="back-store">Đơn hàng</a><a href="/checkout" className="header-cart"><ShoppingCart/><span>Giỏ hàng<small>{count} sản phẩm</small></span>{count>0&&<em>{count}</em>}</a></div></header></>}
const path=location.pathname;
createRoot(document.getElementById('root')).render(<ConfigProvider locale={viVN} theme={{token:{fontFamily:"Arial, sans-serif"}}}>{path.startsWith('/admin')?<React.Suspense fallback={<div style={{padding:40,fontFamily:'sans-serif'}}>Đang tải trang quản trị...</div>}><AdminApp seed={products}/></React.Suspense>:path==='/register'?<RegisterPage/>:path==='/login'?<LoginPage/>:path==='/checkout'?<CheckoutPage/>:path==='/orders'?<OrdersPage/>:path==='/addresses'?<AddressBookPage/>:path==='/profile'?<ProfilePage/>:path.startsWith('/orders/')?<OrderDetailPage/>:path.startsWith('/collections/')?<CollectionPage/>:path.startsWith('/product/')?<ProductDetailsPage/>:<App/>}</ConfigProvider>);
