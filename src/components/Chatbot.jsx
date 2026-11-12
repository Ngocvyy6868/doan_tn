import React, {useEffect, useRef, useState} from 'react';
import {Bot, ChevronDown, History, Maximize2, MessageCircle, Minimize2, Plus, RefreshCw, Send, Sparkles, X} from 'lucide-react';
import './chatbot.css';
import {readStore, writeStore} from './SiteLayout.jsx';

const endpoint = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/chat/`;
const STARTERS = [
 {title:'Gaming 2K', text:'Gaming 2K'},
 {title:'Đồ họa 3D', text:'Đồ họa 3D'},
 {title:'Ngân sách 25 triệu', text:'Ngân sách 25 triệu'},
 {title:'Văn phòng, học tập', text:'Máy văn phòng học tập ngân sách 12 triệu'},
];
const money = value => typeof value === 'number' ? value.toLocaleString('vi-VN') + '₫' : 'Chưa có giá';
const checkLabel = c => c.status === 'pass' ? 'Đạt' : c.code === 'R13' && c.status === 'fail' ? 'Thiếu linh kiện'
 : c.status === 'fail' ? (c.severity === 'warning' ? 'Lưu ý' : 'Xung đột') : c.severity === 'warning' ? 'Chưa xác minh' : 'Chưa đủ dữ liệu';

const CAT_LABEL = {cpu:'CPU', mainboard:'Mainboard', ram:'RAM', gpu:'Card đồ họa', ssd:'SSD', psu:'Nguồn', case:'Vỏ máy', cooler:'Tản nhiệt', license:'Bản quyền'};
const SWAPPABLE = new Set(['cpu', 'mainboard', 'ram', 'gpu', 'ssd', 'psu', 'case', 'cooler']);

// Danh sách sản phẩm cùng nhóm còn bán, lấy từ catalog đã đồng bộ ở trang (giá/tồn sẽ được backend kiểm tra lại).
function SwapPicker({product, disabled, onPick}) {
 const options = readStore('techzone_products', [])
  .filter(p => p.product_type === product.cat && p.id !== product.id && p.active !== false && Number(p.stock) > 0 && Number(p.price) > 0)
  .sort((a, b) => a.price - b.price);
 if (!options.length) return <p className="ai-swap-empty">Chưa có sản phẩm {CAT_LABEL[product.cat] || product.cat} khác còn hàng.</p>;
 return <div className="ai-swap-list" role="listbox" aria-label={`Chọn ${CAT_LABEL[product.cat] || product.cat} thay thế`}>
  {options.map(p => <button type="button" key={p.id} disabled={disabled} onClick={() => onPick(p)}>
   {p.img ? <img src={p.img} alt="" loading="lazy"/> : <span className="ai-product-noimg"/>}
   <span><b>{p.name}</b><small>{money(p.price)} {p.price > product.price ? `(+${money(p.price - product.price)})` : p.price < product.price ? `(−${money(product.price - p.price)})` : ''}</small></span>
  </button>)}
 </div>;
}

// Phương án thay thế do backend tính khi không lắp được đủ bộ (không phải nội dung LLM tự nghĩ).
function Alternatives({data}) {
 const link = p => <a href={`/product/${encodeURIComponent(p.id)}`}>{p.name}</a>;
 return <div className="ai-alt">
  <b>Phương án thay thế</b>
  {data.min_build_total != null && (data.budget_shortfall > 0
   ? <p>Bộ rẻ nhất lắp được từ hàng hiện có là <strong>{money(data.min_build_total)}</strong>. Cần tăng ngân sách linh kiện thêm khoảng <strong>{money(data.budget_shortfall)}</strong>.</p>
   : <p>Ngân sách vẫn đủ cho bộ rẻ nhất lắp được (<strong>{money(data.min_build_total)}</strong>) nếu giảm cấu hình ở các nhóm khác.</p>)}
  {data.brand_unavailable && <p>Không lắp được đủ bộ với hãng CPU đã chọn; phương án trên dùng CPU hãng khác.</p>}
  <ul>{data.missing.map(m => <li key={m.cat}>
   <strong>{CAT_LABEL[m.cat] || m.cat}:</strong>{' '}
   {m.product ? <>rẻ nhất lắp được là {link(m.product)} ({money(m.product.price)}){m.over_by > 0 && <>, vượt hạn mức {money(m.over_by)}</>}.</> : <>chưa có sản phẩm tương thích còn hàng.</>}
   {m.other_brand && <> Hãng khác trong hạn mức: {link(m.other_brand)} ({money(m.other_brand.price)}).</>}
  </li>)}</ul>
 </div>;
}

function readExpanded() {try {return localStorage.getItem('techzone_chat_expanded') === '1';} catch {return false;}}

// Chỉ lỗi tương thích thật (fail, mức lỗi) mới là xung đột; R13 là thiếu linh kiện, mức cảnh báo là lưu ý.
const isConflict = c => c.status === 'fail' && c.severity === 'error' && c.code !== 'R13';
const isMissing = c => c.status === 'fail' && c.code === 'R13';
const isUnverified = c => c.status === 'unknown' || (c.status === 'fail' && c.severity === 'warning');
function Checks({checks}) {
 const [open, setOpen] = useState(false);
 const count = test => checks.filter(test).length;
 const failed = count(isConflict), missing = count(isMissing), unverified = count(isUnverified);
 return <div className={`ai-checks ${failed || missing ? 'has-fail' : ''}`}>
  <button type="button" className="ai-checks-summary" aria-expanded={open} onClick={() => setOpen(!open)}>
   <b>Kiểm tra tương thích</b>
   <span className="chip pass">{count(c => c.status === 'pass')} đạt</span>
   {failed > 0 && <span className="chip fail">{failed} xung đột</span>}
   {missing > 0 && <span className="chip fail">thiếu linh kiện</span>}
   {unverified > 0 && <span className="chip unknown">{unverified} cần lưu ý</span>}
   <ChevronDown className={open ? 'rotated' : ''}/>
  </button>
  {open && <ul>{checks.map((check, i) => <li key={i} className={`ai-check-${check.status}`}>
   <strong>{checkLabel(check)}</strong> — {check.code} {check.rule}{check.severity === 'warning' && ' (cảnh báo)'}
   {check.pair && <small>{check.pair}</small>}<small>{check.message}</small>
  </li>)}</ul>}
 </div>;
}

export default function Chatbot() {
 const [open, setOpen] = useState(false), [expanded, setExpanded] = useState(readExpanded), [messages, setMessages] = useState([]);
 const [input, setInput] = useState(''), [busy, setBusy] = useState(false);
 const [error, setError] = useState(''), [token, setToken] = useState(''), [login, setLogin] = useState(false);
 const [sessions, setSessions] = useState([]), [historyOpen, setHistoryOpen] = useState(false), [swapping, setSwapping] = useState(null);
 const bottom = useRef(null), pending = useRef(false), textarea = useRef(null);
 const loadSessions = () => fetch(endpoint + 'sessions/', {credentials:'include'}).then(r => r.ok ? r.json() : null).then(d => {if (d) setSessions(d.results);}).catch(() => {});
 useEffect(() => {
  if (!open) return;
  const controller = new AbortController();
  fetch(endpoint, {credentials:'include', signal:controller.signal}).then(async response => {
   const data = await response.json();
   if (!response.ok) {setLogin(response.status === 401); throw new Error(data.message || 'Không tải được hội thoại.');}
   setLogin(false); setError(''); setToken(data.csrf_token); setMessages(data.history);
   loadSessions();
  }).catch(e => {if (e.name !== 'AbortError') setError(e.message);});
  return () => controller.abort();
 }, [open]);
 useEffect(() => {bottom.current?.scrollIntoView({behavior:'smooth', block:'end'});}, [messages, busy, open, expanded]);
 useEffect(() => {
  const openChat = () => setOpen(true);
  window.addEventListener('techzone:open-chat', openChat);
  return () => window.removeEventListener('techzone:open-chat', openChat);
 }, []);
 useEffect(() => {try {localStorage.setItem('techzone_chat_expanded', expanded ? '1' : '0');} catch {}}, [expanded]);
 useEffect(() => {
  if (!open) return;
  const onKey = e => {if (e.key === 'Escape') setOpen(false);};
  window.addEventListener('keydown', onKey);
  // Khóa cuộn trang nền khi chat chiếm cả màn hình.
  const lock = expanded || window.matchMedia('(max-width: 720px)').matches;
  if (lock) document.body.style.overflow = 'hidden';
  return () => {window.removeEventListener('keydown', onKey); if (lock) document.body.style.overflow = '';};
 }, [open, expanded]);
 useEffect(() => {
  const el = textarea.current; if (!el) return;
  el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 160) + 'px';
 }, [input, open]);

 async function send(text = input, swapIds = null) {
  text = text.trim();
  if (!text || pending.current || !token || login) return;
  pending.current = true; setBusy(true); setError('');
  setMessages(items => [...items, {role:'user', text, optimistic:true}]); setInput('');
  try {
   const productId = location.pathname.startsWith('/product/') ? decodeURIComponent(location.pathname.split('/')[2] || '') : '';
   const response = await fetch(endpoint, {method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json', 'X-CSRFToken':token},
    // swapIds: khách bấm "Đổi" một linh kiện; backend ghim sản phẩm mới và lắp lại phần còn lại.
    body:JSON.stringify(swapIds ? {message:text, product_ids:swapIds, swap:true} : {message:text, product_ids:productId ? [productId] : []}), signal:AbortSignal.timeout(145000)});
   const data = await response.json();
   if (!response.ok) {setLogin(response.status === 401); throw new Error(data.message || 'Không gửi được câu hỏi. Hãy mở lại chat để thử lại.');}
   setMessages(items => [...items.map(m => m.optimistic ? {role:m.role, text:m.text} : m), {...data, role:'assistant', text:data.answer}]);
   if (messages.length === 0) loadSessions();
  } catch(e) {
   setMessages(items => items.filter(m => !m.optimistic)); setInput(text);
   setError(e.name === 'TimeoutError' ? 'Phản hồi quá lâu. Vui lòng thử lại.' : e.message);
  }
  finally {pending.current = false; setBusy(false); textarea.current?.focus();}
 }

 async function restore(id) {
  if (!id || pending.current) return;
  pending.current = true; setBusy(true);
  try {
   const response = await fetch(endpoint + 'sessions/' + id + '/', {method:'POST', credentials:'include', headers:{'X-CSRFToken':token}});
   const data = await response.json();
   if (!response.ok) throw new Error(data.message || 'Không tải được hội thoại.');
   setMessages(data.history); setError(''); setHistoryOpen(false);
  } catch(e) {setError(e.message);}
  finally {pending.current = false; setBusy(false);}
 }
 async function addBuild(products) {
  if (pending.current) return;
  pending.current = true; setBusy(true); setError('');
  try {
   const buildCats = new Set(products.map(p => p.cat).filter(Boolean));
   const existing = readStore('techzone_cart', []).filter(p => !buildCats.has(p.cat));
   const quantities = new Map(existing.map(p => [p.id, p.q]));
   products.forEach(p => quantities.set(p.id, (quantities.get(p.id) || 0) + 1));
   const response = await fetch(endpoint.replace('/chat/', '/advisor/validate/'), {method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json', 'X-CSRFToken':token},
    body:JSON.stringify({items:[...quantities].map(([id,quantity]) => ({id,quantity}))})});
   const data = await response.json();
   if (!response.ok) throw new Error(data.message || 'Không kiểm tra được cấu hình.');
   if (!data.can_add_to_cart) throw new Error([...data.errors, ...data.checks.filter(c => c.severity === 'error' && c.status !== 'pass').map(c => c.rule + ': ' + c.message)].join(' '));
   writeStore('techzone_cart', data.products.map(p => ({...p, q:p.quantity})));
   window.dispatchEvent(new CustomEvent('techzone:cart'));
   setMessages(items => [...items, {role:'assistant', text:'Đã thêm cấu hình vào giỏ theo giá và tồn kho hiện tại.'}]);
  } catch(e) {setError(e.message);}
  finally {pending.current = false; setBusy(false);}
 }
 async function reset() {
  if (pending.current) return;
  try {
   const response = await fetch(endpoint, {method:'DELETE', credentials:'include', headers:{'X-CSRFToken':token}});
   if (!response.ok) throw new Error('Không thể tạo hội thoại mới.');
   setMessages([]); setError(''); setHistoryOpen(false); loadSessions();
  } catch(e) {setError(e.message);}
 }

 const disabled = busy || !token || login;
 const historyList = <div className="ai-history">
  <button type="button" className="ai-new" disabled={disabled} onClick={reset}><Plus/> Hội thoại mới</button>
  <small>Lịch sử</small>
  {sessions.length ? sessions.map(s => <button type="button" key={s.id} disabled={busy} onClick={() => restore(s.id)}>
   <MessageCircle/><span>{new Date(s.created_at).toLocaleString('vi-VN', {dateStyle:'short', timeStyle:'short'})}</span>
  </button>) : <p>Chưa có hội thoại nào.</p>}
 </div>;

 return <>
  {!open && <button className="chat-fab" aria-expanded={open} onClick={() => setOpen(true)}><MessageCircle/><span>Hỏi AI</span></button>}
  {open && expanded && <div className="ai-backdrop" onClick={() => setOpen(false)}/>}
  {open && <section className={`ai-chat ${expanded ? 'expanded' : 'docked'}`} role="dialog" aria-label="Tư vấn linh kiện TechZone">
   {expanded && <aside className="ai-sidebar">{historyList}</aside>}
   <div className="ai-main">
    <div className="ai-head">
     <span className="ai-avatar"><Sparkles/></span>
     <div><b>TechZone AI</b><small><i/> Tư vấn từ danh mục cửa hàng</small></div>
     <div className="ai-actions">
      <button type="button" className="ai-docked-only" aria-label="Lịch sử hội thoại" aria-expanded={historyOpen} onClick={() => setHistoryOpen(!historyOpen)}><History/></button>
      <button type="button" className="ai-docked-only" aria-label="Hội thoại mới" disabled={disabled} onClick={reset}><Plus/></button>
      <button type="button" className="ai-expand" aria-label={expanded ? 'Thu nhỏ' : 'Mở rộng'} onClick={() => setExpanded(!expanded)}>{expanded ? <Minimize2/> : <Maximize2/>}</button>
      <button type="button" aria-label="Đóng chat" onClick={() => setOpen(false)}><X/></button>
     </div>
    </div>
    {historyOpen && <div className="ai-history-pop">{historyList}</div>}
    <div className="ai-body" role="log" aria-live="polite">
     <div className="ai-thread">
      {!messages.length ? <div className="ai-welcome">
       <span className="ai-avatar big"><Bot/></span>
       <h2>Chào anh/chị! Em là trợ lý build PC của TechZone.</h2>
       <p>Anh/chị cần build PC cho nhu cầu gì và ngân sách khoảng bao nhiêu ạ? Em sẽ chọn linh kiện có sẵn tại cửa hàng và kiểm tra tương thích.</p>
       <div className="ai-starters">{STARTERS.map(s => <button key={s.title} type="button" disabled={disabled} onClick={() => send(s.text)}>{s.title}</button>)}</div>
      </div> : messages.map((message, index) => <div key={index} className={`ai-row ${message.role}`}>
       {message.role !== 'user' && <span className="ai-avatar"><Sparkles/></span>}
       <div className="ai-bubble">
        <p className="ai-text">{message.text}</p>
        {message.products?.length > 0 && <div className="ai-products">{message.products.map(product => {
         const swappable = message.stage === 'recommendation' && index === messages.length - 1 && SWAPPABLE.has(product.cat);
         return <div className="ai-product-wrap" key={product.id}>
          <a className="ai-product" href={`/product/${encodeURIComponent(product.id)}`}>
           {product.img ? <img src={product.img} alt="" loading="lazy"/> : <span className="ai-product-noimg"/>}
           <span><small>{CAT_LABEL[product.cat] || product.cat}</small><b>{product.name}</b><strong>{money(product.price)}</strong></span>
          </a>
          {swappable && <button type="button" className="ai-swap-btn" disabled={disabled} aria-expanded={swapping === product.id}
           onClick={() => setSwapping(swapping === product.id ? null : product.id)}><RefreshCw/> Đổi</button>}
          {swapping === product.id && <SwapPicker product={product} disabled={disabled} onPick={p => {
           setSwapping(null);
           send(`Đổi ${CAT_LABEL[product.cat] || product.cat} sang ${p.name}`, [p.id]);
          }}/>}
         </div>;
        })}</div>}
        {message.total != null && <div className="ai-total"><span>Tổng sản phẩm</span><strong>{money(Number(message.total))}</strong>
         {message.peripheral_reserve > 0 && <small>Dự phòng màn hình/phím/chuột: {money(Number(message.peripheral_reserve))} (chưa chọn sản phẩm)</small>}</div>}
        {message.assumptions?.length > 0 && <ul className="ai-assumptions">{message.assumptions.map((a,i) => <li key={i}>{a}</li>)}</ul>}
        {message.errors?.map((a,i) => <p key={i} className="ai-error">{a}</p>)}
        {message.alternatives?.missing?.length > 0 && <Alternatives data={message.alternatives}/>}
        {message.checks?.length > 0 && <Checks checks={message.checks}/>}
        {message.can_add_to_cart && <button type="button" className="ai-add" disabled={busy} onClick={() => addBuild(message.products)}>Thêm cả bộ vào giỏ</button>}
        {index === messages.length - 1 && message.quick_replies?.map(group => <div key={group.question} className="ai-starters" role="group" aria-label={group.question}>
         {group.options.map(text => <button key={text} type="button" disabled={disabled} onClick={() => send(text)}>{text}</button>)}
        </div>)}
       </div>
      </div>)}
      {busy && <div className="ai-row assistant"><span className="ai-avatar"><Sparkles/></span><div className="ai-bubble ai-typing" role="status"><i/><i/><i/><span>Đang tìm linh kiện và kiểm tra thông số…</span></div></div>}
      <div ref={bottom}/>
     </div>
    </div>
    {error && <div className="ai-error ai-error-bar" role="alert">{error} {login && <a href="/login">Đăng nhập</a>}</div>}
    <form className="ai-composer" onSubmit={event => {event.preventDefault(); send();}}>
     <textarea ref={textarea} rows={1} aria-label="Câu hỏi tư vấn" maxLength={2000} value={input} disabled={busy || login}
      onChange={e => setInput(e.target.value)} placeholder="Nhập nhu cầu, ngân sách hoặc tên linh kiện…"
      onKeyDown={e => {if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); send();}}}/>
     <button aria-label="Gửi câu hỏi" disabled={disabled || !input.trim()}><Send/></button>
    </form>
    <small className="ai-footnote">Enter để gửi · Shift+Enter xuống dòng · Giá và tồn kho lấy từ hệ thống</small>
   </div>
  </section>}
 </>;
}
