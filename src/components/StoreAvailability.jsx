import React,{useEffect,useState} from 'react';
import {CheckCircle2,MapPin,Store} from 'lucide-react';
const api=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api';

// Danh sách cửa hàng còn hàng, lấy trực tiếp từ tồn kho theo kho.
export default function StoreAvailability({productId}){
 const [data,setData]=useState(null);
 useEffect(()=>{
  if(!productId)return;
  const controller=new AbortController();
  setData(null);
  fetch(`${api}/products/${encodeURIComponent(productId)}/availability/`,{signal:controller.signal})
   .then(r=>r.ok?r.json():null).then(setData).catch(()=>{});
  return()=>controller.abort();
 },[productId]);
 if(!data?.managed)return null;
 const stores=data.stores||[];
 return <section className="store-availability" aria-label="Cửa hàng còn hàng">
  <h3><Store/> {stores.length?`Còn hàng tại ${stores.length} cửa hàng`:'Tạm hết hàng tại các cửa hàng'}</h3>
  {stores.length>0?<ul>{stores.map(s=><li key={s.code}>
   <MapPin/><div><b>{s.code}</b><span>{s.address}</span></div>
   <em className={s.quantity<=2?'low':''}><CheckCircle2/>{s.quantity<=2?'Sắp hết':'Còn hàng'}</em>
  </li>)}</ul>:<p>Sản phẩm đang được nhập thêm. Vui lòng liên hệ hotline 1900 6868 để được hỗ trợ.</p>}
 </section>;
}
