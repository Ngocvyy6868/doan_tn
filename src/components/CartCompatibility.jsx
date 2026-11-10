import React, {useEffect, useState} from 'react';
import {Info} from 'lucide-react';
const api = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
// Lỗi chỉ có ý nghĩa khi giỏ là một bộ PC hoàn chỉnh; đơn lẻ không cần báo.
const BUILD_ONLY_ERRORS = ['Có nhiều sản phẩm cùng nhóm', 'Một cấu hình chỉ dùng một sản phẩm mỗi nhóm'];
export default function CartCompatibility({cart}) {
 const [result, setResult] = useState(null), [error, setError] = useState('');
 const signature = JSON.stringify(cart.map(p => ({id:p.id,quantity:p.q})));
 useEffect(() => {
  const controller = new AbortController();
  setResult(null); setError('');
  if (!JSON.parse(signature).length) return () => controller.abort();
  (async () => {
   try {
    const csrf = await fetch(api+'/chat/', {credentials:'include',signal:controller.signal});
    if (!csrf.ok) return;
    const token = (await csrf.json()).csrf_token;
    const response = await fetch(api+'/advisor/validate/', {method:'POST',credentials:'include',
     headers:{'Content-Type':'application/json','X-CSRFToken':token},
     body:JSON.stringify({items:JSON.parse(signature)}),signal:controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không kiểm tra được cấu hình.');
    setResult(data);
   } catch(e) {if (e.name !== 'AbortError') setError(e.message);}
  })();
  return () => controller.abort();
 }, [signature]);
 if (!result) return <div aria-live="polite">{error && <p role="alert">{error}</p>}</div>;
 // Thiếu linh kiện bắt buộc (R13) nghĩa là giỏ là đơn lẻ, không phải một bộ PC.
 const retail = result.checks.some(c => c.code === 'R13' && c.status === 'fail');
 const errors = retail ? result.errors.filter(e => !BUILD_ONLY_ERRORS.some(prefix => e.startsWith(prefix))) : result.errors;
 const issues = result.checks.filter(c => c.code !== 'R13' && (retail ? c.status === 'fail' : c.status !== 'pass'));
 return <div aria-live="polite">
  {retail && <div className="cart-retail-note" role="note"><Info/><div>
   <b>Đơn hàng lẻ, nếu xây dựng cấu hình hãy để chúng tôi tư vấn.</b>
   <button type="button" onClick={() => window.dispatchEvent(new CustomEvent('techzone:open-chat'))}>Hỏi AI tư vấn cấu hình</button>
  </div></div>}
  {(issues.length > 0 || errors.length > 0) && <details open className="cart-compat-issues"><summary>Cần kiểm tra sản phẩm trong giỏ</summary>
   {errors.map((e,i) => <p key={i}>{e}</p>)}
   {issues.map(c => <p key={c.code}>{c.code} {c.rule}: {c.message}{c.severity === 'warning' ? ' (cảnh báo)' : ''}</p>)}
  </details>}
 </div>;
}
