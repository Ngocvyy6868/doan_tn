import React, {useEffect, useRef, useState} from 'react';
import {MessageCircle, Send, Sparkles, X} from 'lucide-react';
import './chatbot.css';

const endpoint = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/chat/`;
export default function Chatbot() {
 const [open, setOpen] = useState(false), [messages, setMessages] = useState([]);
 const [input, setInput] = useState(''), [busy, setBusy] = useState(false);
 const [error, setError] = useState(''), [token, setToken] = useState(''), [login, setLogin] = useState(false);
 const bottom = useRef(null), pending = useRef(false);
 useEffect(() => {
  if (!open) return;
  const controller = new AbortController();
  fetch(endpoint, {credentials:'include', signal:controller.signal}).then(async response => {
   const data = await response.json();
   if (!response.ok) {setLogin(response.status === 401); throw new Error(data.message || 'Không tải được hội thoại.');}
   setLogin(false); setError(''); setToken(data.csrf_token); setMessages(data.history);
  }).catch(e => {if (e.name !== 'AbortError') setError(e.message);});
  return () => controller.abort();
 }, [open]);
 useEffect(() => {bottom.current?.scrollIntoView({behavior:'smooth'});}, [messages, busy, open]);
 async function send(text = input) {
  text = text.trim();
  if (!text || pending.current || !token || login) return;
  pending.current = true; setBusy(true); setError('');
  try {
   const productId = location.pathname.startsWith('/product/') ? decodeURIComponent(location.pathname.split('/')[2] || '') : '';
   const response = await fetch(endpoint, {method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json', 'X-CSRFToken':token},
    body:JSON.stringify({message:text, product_ids:productId ? [productId] : []}), signal:AbortSignal.timeout(70000)});
   const data = await response.json();
   if (!response.ok) {setLogin(response.status === 401); throw new Error(data.message || 'Không gửi được câu hỏi. Hãy mở lại chat để thử lại.');}
   setMessages(items => [...items, {role:'user', text}, {role:'assistant', text:data.answer, products:data.products, checks:data.checks}]);
   setInput('');
  } catch(e) {setError(e.name === 'TimeoutError' ? 'Phản hồi quá lâu. Vui lòng thử lại.' : e.message);}
  finally {pending.current = false; setBusy(false);}
 }
 async function reset() {
  if (pending.current) return;
  try {
   const response = await fetch(endpoint, {method:'DELETE', credentials:'include', headers:{'X-CSRFToken':token}});
   if (!response.ok) throw new Error('Không thể tạo hội thoại mới.');
   setMessages([]); setError('');
  } catch(e) {setError(e.message);}
 }
 return <>
  <button className="chat-fab" aria-expanded={open} onClick={() => setOpen(!open)}><MessageCircle/><span>Hỏi AI</span></button>
  {open && <section className="chat ai-chat" aria-label="Tư vấn linh kiện TechZone">
   <div className="chat-head"><span><Sparkles/> TechZone AI</span><button aria-label="Đóng chat" onClick={() => setOpen(false)}><X/></button></div>
   <div className="ai-toolbar"><small>Tư vấn từ danh mục cửa hàng</small><button disabled={busy || !token || login} onClick={reset}>Hội thoại mới</button></div>
   <div className="chat-body" role="log" aria-live="polite">
    <div className="bot">Chào bạn! Bạn cần build PC cho nhu cầu gì và ngân sách bao nhiêu?</div>
    {!messages.length && <div className="suggest">{['Gaming 2K', 'Đồ họa 3D', 'Ngân sách 25 triệu'].map(text => <button key={text} disabled={busy || !token || login} onClick={() => send(text)}>{text}</button>)}</div>}
    {messages.map((message, index) => <div key={index} className={`ai-message ${message.role}`}>
     <p>{message.text}</p>
     {message.products?.map(product => <a className="ai-product" href={`/product/${encodeURIComponent(product.id)}`} key={product.id}>{product.name}<strong>{typeof product.price === 'number' ? product.price.toLocaleString('vi-VN') + '₫' : 'Chưa có giá'}</strong></a>)}
     {message.checks?.length > 0 && <div className="ai-checks"><b>Kết quả kiểm tra từ hệ thống</b>{message.checks.map((check, i) => <p key={i} className={`ai-check-${check.status}`}>{check.status === 'pass' ? '✓ Đạt' : check.status === 'fail' ? '✕ Xung đột' : '? Chưa đủ dữ liệu'} — {check.rule}<br/>{check.pair}<br/>{check.message}</p>)}</div>}
    </div>)}
    {busy && <p role="status">Đang tìm linh kiện và kiểm tra thông số…</p>}
    <div ref={bottom}/>
   </div>
   {error && <div className="ai-error" role="alert">{error} {login && <a href="/login">Đăng nhập</a>}</div>}
   <form className="chat-input" onSubmit={event => {event.preventDefault(); send();}}><input aria-label="Câu hỏi tư vấn" maxLength={2000} value={input} onChange={e => setInput(e.target.value)} disabled={busy || login} placeholder="Nhập câu hỏi..."/><button aria-label="Gửi câu hỏi" disabled={busy || !token || login || !input.trim()}><Send/></button></form>
  </section>}
 </>;
}
