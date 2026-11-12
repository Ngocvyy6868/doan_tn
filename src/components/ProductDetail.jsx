import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Check,ChevronDown,ChevronLeft,ChevronRight,MessageCircle,Package,Plus,RotateCcw,ShieldCheck,ShoppingCart,Truck} from 'lucide-react';
import {keySpecs,specRows} from './ProductSpecs.jsx';
import StoreAvailability from './StoreAvailability.jsx';
import {categorySlug} from './SiteLayout.jsx';
import './product-detail.css';

const money=n=>Number(n||0).toLocaleString('vi-VN')+'₫';
const discountOf=p=>p.old>p.price?Math.round((1-p.price/p.old)*100):0;
const openChat=()=>window.dispatchEvent(new CustomEvent('techzone:open-chat'));

function Gallery({product}){
 const images=useMemo(()=>[...new Set([...(Array.isArray(product.images)?product.images:[]),product.img].filter(Boolean))],[product]);
 const [index,setIndex]=useState(0);
 const go=step=>setIndex(i=>(i+step+images.length)%images.length);
 if(!images.length)return <div className="pd-gallery-main pd-noimg"><Package/></div>;
 return <div className="pd-gallery">
  <div className="pd-gallery-main">
   <img src={images[index]} alt={`${product.name} - ảnh ${index+1}`}/>
   {images.length>1&&<><button type="button" className="pd-nav prev" aria-label="Ảnh trước" onClick={()=>go(-1)}><ChevronLeft/></button>
    <button type="button" className="pd-nav next" aria-label="Ảnh tiếp theo" onClick={()=>go(1)}><ChevronRight/></button></>}
   <span className="pd-counter">{index+1}/{images.length}</span>
  </div>
  {images.length>1&&<div className="pd-thumbs">{images.map((src,i)=><button type="button" key={src} className={i===index?'active':''} onClick={()=>setIndex(i)} aria-label={`Xem ảnh ${i+1}`}><img src={src} alt=""/></button>)}</div>}
 </div>;
}

function Highlights({product,onSeeAll}){
 const items=keySpecs(product,6);
 if(!items.length)return null;
 return <section className="pd-highlights">
  <div className="pd-section-head"><h3>Thông số nổi bật</h3><button type="button" onClick={onSeeAll}>Xem tất cả thông số <ChevronRight/></button></div>
  <div className="pd-highlight-grid">{items.map(({Icon,label,text})=><div key={label}><small>{label}</small><p><Icon aria-hidden="true"/><b>{text}</b></p></div>)}</div>
 </section>;
}

function SimilarProducts({product,catalog}){
 const rail=useRef(null);
 const items=catalog.filter(p=>p.id!==product.id&&p.active!==false&&p.cat===product.cat).slice(0,12);
 if(!items.length)return null;
 const scroll=dir=>rail.current?.scrollBy({left:dir*rail.current.clientWidth*.8,behavior:'smooth'});
 return <section className="pd-similar">
  <div className="pd-section-head"><h2>Sản phẩm tương tự</h2><div className="pd-rail-nav"><button type="button" aria-label="Xem trước" onClick={()=>scroll(-1)}><ChevronLeft/></button><button type="button" aria-label="Xem tiếp" onClick={()=>scroll(1)}><ChevronRight/></button></div></div>
  <div className="pd-rail" ref={rail}>{items.map(p=>{const d=discountOf(p);return <a key={p.id} className="pd-card" href={`/product/${encodeURIComponent(p.id)}`}>
   <span className="pd-card-img">{p.img?<img src={p.img} alt={p.name} loading="lazy"/>:<Package/>}</span>
   <span className="pd-card-name">{p.name}</span>
   <span className="pd-card-old">{d>0&&<><del>{money(p.old)}</del><em>-{d}%</em></>}</span>
   <strong>{money(p.price)}</strong>
  </a>})}</div>
 </section>;
}

function ProductInfo({product,specsRef}){
 const rows=specRows(product);
 const [expanded,setExpanded]=useState(false);
 const text=[product.description,product.productInfo].filter(Boolean).filter((t,i,a)=>a.indexOf(t)===i);
 return <section className="pd-info" ref={specsRef} id="thong-so">
  <h2>Thông tin sản phẩm</h2>
  <div className={`pd-info-body ${expanded?'expanded':''}`}>
   <h3>Thông số kỹ thuật</h3>
   {rows.length?<table className="pd-spec-table"><tbody>{rows.map((r,i)=><tr key={`${r.label}-${i}`}><th>{r.label}</th><td>{r.value}</td></tr>)}</tbody></table>:<p className="pd-muted">Thông số kỹ thuật đang được cập nhật.</p>}
   <h3>Mô tả sản phẩm</h3>
   {text.length?text.map((t,i)=><p key={i}>{t}</p>):<p className="pd-muted">Thông tin sản phẩm đang được cập nhật.</p>}
   {!expanded&&<div className="pd-info-fade"><button type="button" onClick={()=>setExpanded(true)}>Xem thêm <ChevronDown/></button></div>}
  </div>
 </section>;
}

export default function ProductDetail({product,catalog,onAdd,onBuyNow}){
 const [added,setAdded]=useState(false);
 const specsRef=useRef(null);
 useEffect(()=>{setAdded(false);window.scrollTo(0,0)},[product.id]);
 const unavailable=product.active===false||product.stock<=0;
 const discount=discountOf(product);
 const add=()=>{if(unavailable)return;onAdd(product);setAdded(true)};
 const seeSpecs=()=>specsRef.current?.scrollIntoView({behavior:'smooth',block:'start'});
 return <div className="pd">
  <nav className="pd-breadcrumb" aria-label="Breadcrumb"><a href="/">Trang chủ</a><span>/</span><a href={`/collections/${categorySlug(String(product.cat||''))}`}>{product.cat}</a><span>/</span><b>{product.name}</b></nav>
  <div className="pd-top">
   <div className="pd-left">
    <Gallery product={product}/>
    <Highlights product={product} onSeeAll={seeSpecs}/>
   </div>
   <div className="pd-right">
    <div className="pd-panel">
     <div className="pd-title">
      <h1>{product.name}</h1>
      <div className="pd-meta">{product.brand&&<span>Thương hiệu: <b>{product.brand}</b></span>}{product.sku&&<span>SKU: <b>{product.sku}</b></span>}<button type="button" onClick={seeSpecs}>Thông số kỹ thuật</button></div>
     </div>
     <div className="pd-price"><strong>{money(product.price)}</strong>{discount>0&&<><del>{money(product.old)}</del><em>-{discount}%</em></>}</div>
     <div className={`pd-stock ${unavailable?'out':''}`}><Check/>{unavailable?'Tạm hết hàng':`Còn hàng${Number.isFinite(product.stock)?` (${product.stock} sản phẩm)`:''}`}</div>
     <div className="pd-actions">
      <button type="button" className="pd-buy" disabled={unavailable} onClick={()=>onBuyNow(product)}><b>Mua ngay</b><small>Giao tận nơi hoặc nhận tại cửa hàng</small></button>
      <button type="button" className="pd-consult" onClick={openChat}><b><MessageCircle/> Tư vấn ngay</b><small>Hỏi AI chọn linh kiện phù hợp</small></button>
      <button type="button" className={`pd-cart ${added?'added':''}`} disabled={unavailable} onClick={add} aria-label={added?'Đã thêm vào giỏ':'Thêm vào giỏ hàng'} title={added?'Đã thêm vào giỏ':'Thêm vào giỏ hàng'}>
       {added?<Check/>:<span className="pd-cart-icon"><ShoppingCart/><i><Plus/></i></span>}
      </button>
     </div>
     <section className="pd-policy" aria-label="Chính sách">
      <p><ShieldCheck/><span><b>Bảo hành chính hãng</b> theo chính sách của nhà sản xuất.</span></p>
      <p><Truck/><span><b>Giao hàng toàn quốc</b>, miễn phí cho đơn từ 20 triệu.</span></p>
      <p><RotateCcw/><span><b>Đổi mới trong 30 ngày</b> nếu lỗi do nhà sản xuất.</span></p>
     </section>
     <StoreAvailability productId={product.id}/>
    </div>
   </div>
  </div>
  <SimilarProducts product={product} catalog={catalog}/>
  <ProductInfo product={product} specsRef={specsRef}/>
  <div className="pd-mobile-bar">
   <button type="button" className="pd-buy" disabled={unavailable} onClick={()=>onBuyNow(product)}>Mua ngay</button>
   <button type="button" className="pd-consult" onClick={openChat}><MessageCircle/> Tư vấn</button>
   <button type="button" className="pd-cart" disabled={unavailable} onClick={add} aria-label="Thêm vào giỏ hàng">{added?<Check/>:<ShoppingCart/>}</button>
  </div>
 </div>;
}
