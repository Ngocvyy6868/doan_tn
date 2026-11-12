import React,{useCallback,useEffect,useMemo,useState} from 'react';
import {App,Avatar,Badge,Button,Checkbox,Col,Dropdown,Empty,Form,Input,Modal,Popconfirm,Popover,Radio,Row,Segmented,Select,Space,Spin,Switch,Table,Tabs,Tag,Tooltip,Typography} from 'antd';
import {ArrowLeftOutlined,ArrowRightOutlined,CalendarOutlined,CaretDownOutlined,CheckCircleFilled,CheckOutlined,ColumnHeightOutlined,DeleteOutlined,EditOutlined,EnvironmentOutlined,FileTextOutlined,FilterOutlined,LoginOutlined,MailOutlined,MessageOutlined,MoreOutlined,PhoneOutlined,PlusOutlined,PushpinFilled,PushpinOutlined,ReloadOutlined,RightOutlined,ScheduleOutlined,ShoppingCartOutlined,SolutionOutlined,SyncOutlined,UserAddOutlined,UserOutlined} from '@ant-design/icons';
import locations from '../assets/vn-locations.json';
import AdminOrderDetails from './AdminOrderDetails.jsx';
import './customer-profile.css';

const api=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api';
async function request(path,method='GET',body){const r=await fetch(api+path,{method,credentials:'include',...(body?{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});const data=await r.json().catch(()=>({}));if(!r.ok){const error=Error(r.status===403?'Vui lòng đăng nhập bằng tài khoản quản trị để xem Profile khách hàng.':data.message||'Không thể tải dữ liệu.');error.status=r.status;throw error}return data}
const money=v=>Number(v||0).toLocaleString('vi-VN')+' ₫';
const dateTime=v=>v?new Date(v).toLocaleString('vi-VN',{day:'numeric',month:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit'}):'';
const date=v=>v?new Date(v).toLocaleDateString('vi-VN'):'';
const monthLabel=v=>{const d=new Date(v);return `Thg ${d.getMonth()+1}, ${d.getFullYear()}`};
const daysAgo=v=>{if(!v)return null;const days=Math.floor((Date.now()-new Date(v))/864e5);return days<=0?'hôm nay':`${days} ngày trước`};
const empty=<span className="cp-empty">– –</span>;
const ORDER_STATUS={PENDING_PAYMENT:'Chờ thanh toán',CONFIRMED:'Đã xác nhận',PACKING:'Đang đóng gói',DELIVERING:'Đang giao',DELIVERED:'Đã giao',CANCELLED:'Đã hủy'};
const PAYMENT={PAID:'Đã thanh toán',UNPAID:'Chưa thanh toán',REFUNDED:'Đã hoàn tiền'};
const TIER_COLOR={'Kim cương':'purple','Vàng':'gold','Bạc':'default','Thành viên':'blue'};
const RANGES=[{value:'7',label:'7 ngày trước'},{value:'30',label:'30 ngày trước'},{value:'90',label:'90 ngày trước'},{value:'365',label:'1 năm trước'},{value:'all',label:'Toàn bộ thời gian'}];
const EVENT_ICON={REGISTERED:<UserAddOutlined/>,LOGIN:<LoginOutlined/>,PROFILE_UPDATED:<UserOutlined/>,ADDRESS_ADDED:<EnvironmentOutlined/>,ADDRESS_UPDATED:<EnvironmentOutlined/>,ADDRESS_DELETED:<EnvironmentOutlined/>,ORDER_PLACED:<ShoppingCartOutlined/>,ORDER_STATUS:<SyncOutlined/>,CHAT_STARTED:<MessageOutlined/>,NOTE_ADDED:<FileTextOutlined/>,TASK_CREATED:<ScheduleOutlined/>,TASK_COMPLETED:<CheckOutlined/>};

/* Một dòng tóm tắt dưới tiêu đề sự kiện khi đang thu gọn. */
function eventSummary(e){const d=e.data||{};switch(e.type){
 case 'ORDER_PLACED':return `Tổng ${money(d.grand_total)} · ${(d.items||[]).reduce((s,i)=>s+(i.quantity||0),0)} sản phẩm`;
 case 'ORDER_STATUS':return `${d.from_label} → ${d.to_label}`;
 case 'PROFILE_UPDATED':return 'Thay đổi: '+(d.changes||[]).map(c=>c.field).join(', ');
 case 'ADDRESS_ADDED':case 'ADDRESS_UPDATED':case 'ADDRESS_DELETED':return d.address;
 case 'CHAT_STARTED':return d.message?`“${d.message}”`:'';
 case 'NOTE_ADDED':return d.content;
 case 'TASK_CREATED':case 'TASK_COMPLETED':return [d.type_label,d.channel,d.order&&`Đơn ${d.order}`].filter(Boolean).join(' · ');
 case 'REGISTERED':return [d.email,d.phone].filter(Boolean).join(' · ');
 case 'LOGIN':return d.ip?`IP ${d.ip}`:'';
 default:return ''}}

function EventDetail({event,openOrders}){const d=event.data||{};
 const rows=[];const add=(k,v)=>v!==undefined&&v!==null&&v!==''&&rows.push([k,v]);
 if(event.type==='ORDER_PLACED'){add('Mã đơn',<Button type="link" size="small" onClick={openOrders}>{d.code}</Button>);add('Tổng tiền',money(d.grand_total));add('Thanh toán',d.payment_method);add('Trạng thái lúc đặt',ORDER_STATUS[d.status]||d.status);add('Sản phẩm',<ul className="cp-detail-list">{(d.items||[]).map((i,k)=><li key={k}>{i.name} × {i.quantity}</li>)}</ul>)}
 else if(event.type==='ORDER_STATUS'){add('Mã đơn',<Button type="link" size="small" onClick={openOrders}>{d.code}</Button>);add('Trạng thái',`${d.from_label} → ${d.to_label}`)}
 else if(event.type==='PROFILE_UPDATED')add('Thay đổi',<ul className="cp-detail-list">{(d.changes||[]).map((c,k)=><li key={k}><b>{c.field}</b>{c.from!==undefined&&<>: <s>{c.from||'trống'}</s> → {c.to||'trống'}</>}</li>)}</ul>);
 else if(event.type.startsWith('ADDRESS')){add('Địa chỉ',d.address);add('Mặc định',d.default===undefined?null:d.default?'Có':'Không')}
 else if(event.type==='CHAT_STARTED')add('Câu hỏi đầu tiên',d.message||'–');
 else if(event.type==='NOTE_ADDED')add('Nội dung',<span className="cp-pre">{d.content}</span>);
 else if(event.type.startsWith('TASK')){add('Loại',d.type_label);add('Kênh',d.channel);add('Đơn liên quan',d.order);add('Kết quả',d.result&&<span className="cp-pre">{d.result}</span>)}
 else if(event.type==='REGISTERED'){add('E-mail',d.email);add('Số điện thoại',d.phone)}
 else if(event.type==='LOGIN')add('Địa chỉ IP',d.ip);
 add('Thực hiện bởi',event.source==='customer'?'Khách hàng':event.actor||'Hệ thống');
 return <dl className="cp-event-detail">{rows.map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl>}

function EventsTab({base,reloadKey,openOrders}){
 const [range,setRange]=useState('30'),[types,setTypes]=useState([]),[source,setSource]=useState(''),[data,setData]=useState({results:[],types:[],total:0}),[loading,setLoading]=useState(true),[error,setError]=useState(''),[open,setOpen]=useState({});
 useEffect(()=>{let live=true;setLoading(true);setError('');const q=new URLSearchParams({days:range,...(types.length?{types:types.join(',')}:{}),...(source?{source}:{})});request(`${base}/events/?${q}`).then(r=>live&&setData(r)).catch(e=>live&&setError(e.message)).finally(()=>live&&setLoading(false));return()=>{live=false}},[base,range,types,source,reloadKey]);
 const groups=useMemo(()=>{const out=[];for(const e of data.results){const label=monthLabel(e.created_at);if(!out.length||out.at(-1).label!==label)out.push({label,items:[]});out.at(-1).items.push(e)}return out},[data.results]);
 const allOpen=data.results.length>0&&data.results.every(e=>open[e.id]);
 const filter=<div className="cp-filter"><Typography.Text strong>Loại sự kiện</Typography.Text><Checkbox.Group value={types} onChange={setTypes} options={data.types}/><Typography.Text strong>Thực hiện bởi</Typography.Text><Radio.Group value={source} onChange={e=>setSource(e.target.value)} options={[{value:'',label:'Tất cả'},{value:'customer',label:'Khách hàng'},{value:'staff',label:'Nhân viên'}]}/><Button size="small" onClick={()=>{setTypes([]);setSource('')}}>Xóa bộ lọc</Button></div>;
 return <div className="cp-events">
  <div className="cp-toolbar"><Select value={range} onChange={setRange} options={RANGES} prefix={<CalendarOutlined/>} style={{width:210}}/><Typography.Text type="secondary">{data.total} sự kiện</Typography.Text><span className="cp-grow"/><Popover trigger="click" placement="bottomRight" content={filter}><Badge dot={types.length>0||!!source}><Button icon={<FilterOutlined/>} aria-label="Lọc sự kiện"/></Badge></Popover><Tooltip title={allOpen?'Thu gọn tất cả':'Mở rộng tất cả'}><Button icon={<ColumnHeightOutlined/>} aria-label="Mở rộng hoặc thu gọn" onClick={()=>setOpen(allOpen?{}:Object.fromEntries(data.results.map(e=>[e.id,true])))}/></Tooltip></div>
  <div className="cp-timeline-wrap">{loading?<div className="cp-center"><Spin/></div>:error?<div className="cp-center"><Typography.Text type="danger">{error}</Typography.Text></div>:!groups.length?<Empty className="cp-center" description="Không có sự kiện trong khoảng thời gian này."/>:
   <div className="cp-timeline"><div className="cp-axis-labels"><span>Khách hàng</span><span>Nhân viên / Hệ thống</span></div>{groups.map(g=><section key={g.label}><div className="cp-month"><span>{g.label}</span></div>{g.items.map(e=>{const staff=e.source!=='customer';const expanded=!!open[e.id];const summary=eventSummary(e);
    return <div key={e.id} className={`cp-event ${staff?'is-staff':'is-customer'}`}><span className="cp-event-icon" aria-hidden>{EVENT_ICON[e.type]||<SolutionOutlined/>}</span><div className="cp-event-card"><button type="button" className="cp-event-head" aria-expanded={expanded} onClick={()=>setOpen(o=>({...o,[e.id]:!o[e.id]}))}><RightOutlined className={expanded?'cp-rot':''}/><span><b>{e.title}</b>{summary&&!expanded&&<small className="cp-summary">{summary}</small>}<small>{staff&&e.actor?`${e.actor} · `:''}{dateTime(e.created_at)}</small></span></button>{expanded&&<EventDetail event={e} openOrders={openOrders}/>}</div></div>})}</section>)}</div>}</div>
 </div>}

const TASK_COLOR={CONTACT:'blue',COMPLAINT:'red',CONSULT:'cyan',CARE:'green',OTHER:'default'};
function TasksTab({base,reloadKey,onChanged,composer,setComposer}){
 const {message}=App.useApp();const [data,setData]=useState({results:[],options:{types:[],statuses:[],channels:[],assignees:[],orders:[]}}),[loading,setLoading]=useState(true),[error,setError]=useState(''),[view,setView]=useState('TODO'),[saving,setSaving]=useState(false),[finish,setFinish]=useState(null);const [form]=Form.useForm(),[finishForm]=Form.useForm();
 const load=useCallback(()=>{setLoading(true);setError('');return request(`${base}/tasks/`).then(setData).catch(e=>setError(e.message)).finally(()=>setLoading(false))},[base]);
 useEffect(()=>{load()},[load,reloadKey]);
 const initial=useMemo(()=>{if(!composer)return{};const t=composer.task;return t?{type:t.type,status:t.status,title:t.title,description:t.description,channel:t.channel||undefined,result:t.result,order_id:t.order?.id,assignee_id:t.assignee?.id,due_at:t.due_at?toLocal(t.due_at):''}:{type:'CONTACT',status:'TODO',...composer.defaults}},[composer]);
 const save=async(path,method,body,ok)=>{setSaving(true);try{await request(path,method,body);message.success(ok);await load();onChanged();return true}catch(e){message.error(e.message);return false}finally{setSaving(false)}};
 const submit=async v=>{const body={...v,due_at:v.due_at?new Date(v.due_at).toISOString():null,channel:v.channel||'',order_id:v.order_id??null,assignee_id:v.assignee_id??null};const t=composer.task;if(await save(t?`${base}/tasks/${t.id}/`:`${base}/tasks/`,t?'PATCH':'POST',body,t?'Đã cập nhật công việc.':'Đã tạo công việc.'))setComposer(null)};
 const doneLabel=type=>data.options.types.find(t=>t.value===type)?.done_label||'Hoàn thành';
 const list=data.results.filter(t=>view==='ALL'||t.status===view);
 const counts=Object.fromEntries(['TODO','DONE','CANCELLED'].map(s=>[s,data.results.filter(t=>t.status===s).length]));
 const statusValue=Form.useWatch('status',form),typeValue=Form.useWatch('type',form);
 return <div className="cp-pane">
  <div className="cp-toolbar"><Segmented value={view} onChange={setView} options={[{value:'TODO',label:`Cần làm (${counts.TODO})`},{value:'DONE',label:`Hoàn thành (${counts.DONE})`},{value:'CANCELLED',label:`Đã hủy (${counts.CANCELLED})`},{value:'ALL',label:'Tất cả'}]}/><span className="cp-grow"/><Button onClick={()=>setComposer({defaults:{type:'CONTACT',status:'DONE'}})} icon={<PhoneOutlined/>}>Ghi nhận đã liên hệ</Button><Button onClick={()=>setComposer({defaults:{type:'COMPLAINT',status:'TODO'}})}>Ghi nhận phản ánh</Button><Button type="primary" icon={<PlusOutlined/>} onClick={()=>setComposer({})}>Tạo công việc</Button></div>
  {loading?<div className="cp-center"><Spin/></div>:error?<Typography.Text type="danger">{error}</Typography.Text>:!list.length?<Empty className="cp-center" description={view==='TODO'?'Không có công việc cần làm.':'Chưa có công việc.'}/>:
  <div className="cp-cards">{list.map(t=><div key={t.id} className={`cp-task ${t.status!=='TODO'?'is-closed':''} ${t.overdue?'is-overdue':''}`}>
   <Tooltip title={t.status==='TODO'?`Đánh dấu “${doneLabel(t.type)}”`:''}><button type="button" className="cp-check" disabled={t.status!=='TODO'||saving} aria-label="Hoàn thành công việc" onClick={()=>setFinish(t)}>{t.status==='DONE'?<CheckCircleFilled/>:<span/>}</button></Tooltip>
   <div className="cp-task-body"><div className="cp-task-title"><b>{t.title}</b><Tag color={TASK_COLOR[t.type]}>{t.type_label}</Tag><Tag color={t.status==='DONE'?'success':t.status==='CANCELLED'?'default':'processing'}>{t.status_label}</Tag></div>
    {t.description&&<p className="cp-pre">{t.description}</p>}
    {t.result&&<p className="cp-task-result"><b>Kết quả:</b> <span className="cp-pre">{t.result}</span></p>}
    <div className="cp-meta">{t.channel_label&&<span>Kênh: {t.channel_label}</span>}{t.order&&<span>Đơn: {t.order.code}</span>}{t.due_at&&<span className={t.overdue?'cp-danger':''}>Hạn: {dateTime(t.due_at)}{t.overdue&&' (quá hạn)'}</span>}{t.assignee&&<span>Phụ trách: {t.assignee.name}</span>}<span>{t.completed_at?`Xong ${dateTime(t.completed_at)}`:`Tạo ${dateTime(t.created_at)}${t.created_by?' bởi '+t.created_by:''}`}</span></div></div>
   <Dropdown trigger={['click']} menu={{items:[{key:'edit',icon:<EditOutlined/>,label:'Sửa',onClick:()=>setComposer({task:t})},t.status==='TODO'&&{key:'cancel',label:'Hủy công việc',onClick:()=>save(`${base}/tasks/${t.id}/`,'PATCH',{status:'CANCELLED'},'Đã hủy công việc.')},t.status!=='TODO'&&{key:'reopen',label:'Mở lại',onClick:()=>save(`${base}/tasks/${t.id}/`,'PATCH',{status:'TODO'},'Đã mở lại công việc.')},{type:'divider'},{key:'delete',danger:true,icon:<DeleteOutlined/>,label:'Xóa',onClick:()=>Modal.confirm({title:'Xóa công việc này?',okText:'Xóa',okButtonProps:{danger:true},cancelText:'Hủy',onOk:()=>save(`${base}/tasks/${t.id}/`,'DELETE',null,'Đã xóa công việc.')})}].filter(Boolean)}}><Button type="text" icon={<MoreOutlined/>} aria-label="Thao tác"/></Dropdown>
  </div>)}</div>}
  <Modal width={620} title={composer?.task?'Sửa công việc':'Công việc chăm sóc khách hàng'} open={!!composer} onCancel={()=>!saving&&setComposer(null)} onOk={()=>form.submit()} confirmLoading={saving} okText="Lưu" cancelText="Hủy" destroyOnHidden>
   <Form form={form} layout="vertical" onFinish={submit} initialValues={initial} preserve={false}>
    <Row gutter={12}><Col span={12}><Form.Item name="type" label="Loại công việc" rules={[{required:true}]}><Select options={data.options.types}/></Form.Item></Col><Col span={12}><Form.Item name="status" label="Trạng thái"><Select options={data.options.statuses.map(s=>s.value==='DONE'?{...s,label:doneLabel(typeValue)}:s)}/></Form.Item></Col></Row>
    <Form.Item name="title" label="Tiêu đề" extra="Để trống sẽ dùng tên loại công việc." rules={[{max:255}]}><Input placeholder="VD: Gọi xác nhận đơn hàng, phản ánh giao chậm..."/></Form.Item>
    <Form.Item name="description" label="Mô tả / nội dung phản ánh"><Input.TextArea rows={3}/></Form.Item>
    <Row gutter={12}><Col span={12}><Form.Item name="channel" label="Kênh liên hệ"><Select allowClear options={data.options.channels}/></Form.Item></Col><Col span={12}><Form.Item name="order_id" label="Đơn hàng liên quan"><Select allowClear showSearch optionFilterProp="label" options={data.options.orders} notFoundContent="Khách chưa có đơn"/></Form.Item></Col></Row>
    <Row gutter={12}><Col span={12}><Form.Item name="assignee_id" label="Người phụ trách"><Select allowClear showSearch optionFilterProp="label" options={data.options.assignees}/></Form.Item></Col><Col span={12}><Form.Item name="due_at" label="Hạn xử lý"><Input type="datetime-local"/></Form.Item></Col></Row>
    {statusValue==='DONE'&&<Form.Item name="result" label="Kết quả xử lý"><Input.TextArea rows={3} placeholder="VD: Đã gọi, khách đồng ý đổi sản phẩm..."/></Form.Item>}
   </Form>
  </Modal>
  <Modal title={finish?doneLabel(finish.type):''} open={!!finish} onCancel={()=>!saving&&setFinish(null)} okText="Hoàn thành" cancelText="Hủy" confirmLoading={saving} onOk={()=>finishForm.submit()} destroyOnHidden>
   <Typography.Paragraph type="secondary">{finish?.title}</Typography.Paragraph>
   <Form form={finishForm} layout="vertical" preserve={false} onFinish={async v=>{if(await save(`${base}/tasks/${finish.id}/`,'PATCH',{status:'DONE',result:v.result||finish.result||''},'Đã hoàn thành công việc.'))setFinish(null)}}><Form.Item name="result" label="Kết quả xử lý"><Input.TextArea rows={3} autoFocus/></Form.Item></Form>
  </Modal>
 </div>}
function toLocal(iso){const d=new Date(iso);const p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`}

function NotesTab({base,reloadKey,onChanged,focus}){
 const {message}=App.useApp();const [notes,setNotes]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[draft,setDraft]=useState(''),[editing,setEditing]=useState(null),[saving,setSaving]=useState(false);
 const load=useCallback(()=>{setLoading(true);setError('');return request(`${base}/notes/`).then(r=>setNotes(r.results)).catch(e=>setError(e.message)).finally(()=>setLoading(false))},[base]);
 useEffect(()=>{load()},[load,reloadKey]);
 const save=async(path,method,body,ok)=>{setSaving(true);try{await request(path,method,body);if(ok)message.success(ok);await load();onChanged();return true}catch(e){message.error(e.message);return false}finally{setSaving(false)}};
 return <div className="cp-pane">
  <div className="cp-note-editor"><Input.TextArea autoFocus={focus} rows={3} maxLength={5000} showCount value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Ghi chú về khách hàng: sở thích, nhu cầu, lưu ý khi chăm sóc..."/><Button type="primary" disabled={!draft.trim()} loading={saving} onClick={async()=>{if(await save(`${base}/notes/`,'POST',{content:draft},'Đã lưu ghi chú.'))setDraft('')}}>Lưu ghi chú</Button></div>
  {loading?<div className="cp-center"><Spin/></div>:error?<Typography.Text type="danger">{error}</Typography.Text>:!notes.length?<Empty className="cp-center" description="Chưa có ghi chú."/>:
  <div className="cp-cards">{notes.map(n=><div key={n.id} className={`cp-note ${n.pinned?'is-pinned':''}`}>
   <div className="cp-note-head"><Avatar size={28}>{(n.author||'?')[0]}</Avatar><span><b>{n.author||'Nhân viên đã xóa'}</b><small>{dateTime(n.created_at)}{n.updated_at!==n.created_at&&new Date(n.updated_at)-new Date(n.created_at)>1000?' · đã sửa':''}</small></span><span className="cp-grow"/>
    <Tooltip title={n.pinned?'Bỏ ghim':'Ghim lên đầu'}><Button type="text" icon={n.pinned?<PushpinFilled/>:<PushpinOutlined/>} onClick={()=>save(`${base}/notes/${n.id}/`,'PATCH',{pinned:!n.pinned})}/></Tooltip>
    <Button type="text" icon={<EditOutlined/>} aria-label="Sửa ghi chú" onClick={()=>setEditing({id:n.id,content:n.content})}/>
    <Popconfirm title="Xóa ghi chú này?" okText="Xóa" cancelText="Hủy" onConfirm={()=>save(`${base}/notes/${n.id}/`,'DELETE',null,'Đã xóa ghi chú.')}><Button type="text" danger icon={<DeleteOutlined/>} aria-label="Xóa ghi chú"/></Popconfirm></div>
   {editing?.id===n.id?<div className="cp-note-edit"><Input.TextArea rows={3} maxLength={5000} value={editing.content} onChange={e=>setEditing({...editing,content:e.target.value})}/><Space><Button onClick={()=>setEditing(null)}>Hủy</Button><Button type="primary" loading={saving} disabled={!editing.content.trim()} onClick={async()=>{if(await save(`${base}/notes/${n.id}/`,'PATCH',{content:editing.content},'Đã cập nhật ghi chú.'))setEditing(null)}}>Lưu</Button></Space></div>:<p className="cp-pre">{n.content}</p>}
  </div>)}</div>}
 </div>}

function OrdersTab({base,reloadKey,profile}){
 const [orders,setOrders]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 useEffect(()=>{let live=true;setLoading(true);request(`${base}/orders/`).then(r=>live&&setOrders(r.results)).catch(e=>live&&setError(e.message)).finally(()=>live&&setLoading(false));return()=>{live=false}},[base,reloadKey]);
 const s=profile?.stats||{};
 return <div className="cp-pane">
  <div className="cp-kpis">{[['Tổng chi tiêu',money(s.total_spent)],['Số đơn thành công',s.orders??0],['Giá trị đơn trung bình',money(s.average_order)],['Đơn đã hủy',s.cancelled??0]].map(([k,v])=><div key={k}><small>{k}</small><b>{v}</b></div>)}</div>
  {error?<Typography.Text type="danger">{error}</Typography.Text>:<Table rowKey="id" loading={loading} dataSource={orders} pagination={{pageSize:8}} scroll={{x:'max-content'}} locale={{emptyText:'Khách hàng chưa có đơn hàng.'}} expandable={{expandedRowRender:o=><AdminOrderDetails order={o}/>}} columns={[{title:'MÃ ĐƠN',dataIndex:'code'},{title:'NGÀY MUA',dataIndex:'created_at',render:dateTime},{title:'SL',align:'center',render:(_,o)=>o.items.reduce((n,i)=>n+i.quantity,0)},{title:'TRẠNG THÁI',dataIndex:'status',render:v=><Tag color={v==='CANCELLED'?'red':v==='DELIVERED'?'green':'blue'}>{ORDER_STATUS[v]||v}</Tag>},{title:'THANH TOÁN',dataIndex:'payment_status',render:v=>PAYMENT[v]||v},{title:'TỔNG TIỀN',align:'right',render:(_,o)=><b>{money(o.totals.grand_total)}</b>}]}/>}
 </div>}

function AddressTab({base,onChanged}){
 const {message}=App.useApp();const [addresses,setAddresses]=useState([]),[loading,setLoading]=useState(true),[editor,setEditor]=useState(null),[saving,setSaving]=useState(false);const [form]=Form.useForm();const province=Form.useWatch('provinceCode',form);
 const load=useCallback(()=>request(`${base}/addresses/`).then(r=>setAddresses(r.results)).catch(e=>message.error(e.message)).finally(()=>setLoading(false)),[base,message]);
 useEffect(()=>{load()},[load]);
 const mutate=async(path,method,body)=>{setSaving(true);try{await request(base+path,method,body);await load();onChanged();message.success('Đã cập nhật sổ địa chỉ.');return true}catch(e){message.error(e.message);return false}finally{setSaving(false)}};
 const edit=a=>{form.resetFields();form.setFieldsValue(a||{isDefault:!addresses.length});setEditor(a||{})};
 const save=async v=>{const p=locations.provinces.find(p=>p.code===v.provinceCode),w=(locations.wardsByProvince[v.provinceCode]||[]).find(w=>w.code===v.wardCode);if(await mutate('/addresses/'+(editor.id?editor.id+'/':''),editor.id?'PATCH':'POST',{...v,provinceName:p?.name||'',wardName:w?.name||''}))setEditor(null)};
 return <div className="cp-pane"><div className="cp-toolbar"><span className="cp-grow"/><Button type="primary" icon={<PlusOutlined/>} disabled={saving} onClick={()=>edit()}>Thêm địa chỉ</Button></div>
  <Table rowKey="id" loading={loading} dataSource={addresses} tableLayout="fixed" pagination={false} scroll={{x:820}} locale={{emptyText:'Khách hàng chưa có địa chỉ.'}} columns={[{title:'NGƯỜI NHẬN',width:220,render:(_,a)=><Space direction="vertical" size={2}><b>{a.fullName}</b>{a.phone}{a.isDefault&&<Tag color="blue">Mặc định</Tag>}</Space>},{title:'ĐỊA CHỈ',width:340,render:(_,a)=>[a.detail,a.wardName,a.provinceName].join(', ')},{title:'THAO TÁC',width:260,render:(_,a)=><Space wrap><Button size="small" disabled={saving} onClick={()=>edit(a)}>Sửa</Button>{!a.isDefault&&<Button size="small" disabled={saving} onClick={()=>mutate(`/addresses/${a.id}/`,'PATCH',{isDefault:true})}>Đặt mặc định</Button>}<Popconfirm title="Xóa địa chỉ này?" okText="Xóa" cancelText="Hủy" onConfirm={()=>mutate(`/addresses/${a.id}/`,'DELETE')}><Button size="small" danger disabled={saving||addresses.length<=1}>Xóa</Button></Popconfirm></Space>}]}/>
  <Modal width={620} title={editor?.id?'Sửa địa chỉ':'Thêm địa chỉ'} open={!!editor} onCancel={()=>!saving&&setEditor(null)} onOk={()=>form.submit()} confirmLoading={saving} okText="Lưu" cancelText="Hủy"><Form form={form} layout="vertical" onFinish={save}><Form.Item name="fullName" label="Người nhận" rules={[{required:true,whitespace:true,message:'Nhập tên người nhận'},{max:150}]}><Input/></Form.Item><Form.Item name="phone" label="Số điện thoại" rules={[{required:true,pattern:/^0\d{9}$/,message:'Nhập số điện thoại gồm 10 chữ số'}]}><Input maxLength={10}/></Form.Item><Form.Item name="provinceCode" label="Tỉnh / thành phố" rules={[{required:true,message:'Chọn tỉnh / thành phố'}]}><Select showSearch optionFilterProp="label" options={locations.provinces.map(p=>({value:p.code,label:p.name}))} onChange={()=>form.setFieldValue('wardCode',undefined)}/></Form.Item><Form.Item name="wardCode" label="Phường / xã" rules={[{required:true,message:'Chọn phường / xã'}]}><Select disabled={!province} showSearch optionFilterProp="label" options={(locations.wardsByProvince[province]||[]).map(w=>({value:w.code,label:w.name}))}/></Form.Item><Form.Item name="detail" label="Địa chỉ chi tiết" rules={[{required:true,whitespace:true,message:'Nhập địa chỉ chi tiết'}]}><Input.TextArea/></Form.Item><Form.Item name="isDefault" label="Địa chỉ mặc định" valuePropName="checked"><Switch/></Form.Item></Form></Modal>
 </div>}

export default function CustomerProfile({customer,onBack}){
 const base=`/admin/customers/${customer.id}`;
 const [profile,setProfile]=useState(null),[error,setError]=useState(''),[tab,setTab]=useState('events'),[reloadKey,setReloadKey]=useState(0),[composer,setComposer]=useState(null),[focusNote,setFocusNote]=useState(false);
 const loadProfile=useCallback(()=>request(`${base}/profile/`).then(r=>{setProfile(r.profile);setError('')}).catch(e=>setError(e.message)),[base]);
 useEffect(()=>{loadProfile()},[loadProfile,reloadKey]);
 useEffect(()=>{const refresh=()=>setReloadKey(k=>k+1);window.addEventListener('admin-auth-changed',refresh);return()=>window.removeEventListener('admin-auth-changed',refresh)},[]);
 const changed=()=>{loadProfile();setReloadKey(k=>k+1)};
 const newTask=defaults=>{setTab('tasks');setComposer({defaults})};
 const p=profile||{...customer,stats:{}};const s=p.stats||{};
 const contact={items:[{key:'call',icon:<PhoneOutlined/>,label:<a href={`tel:${p.phone}`}>Gọi {p.phone}</a>,disabled:!p.phone},{key:'mail',icon:<MailOutlined/>,label:<a href={`mailto:${p.email}`}>Gửi email</a>,disabled:!p.email},{type:'divider'},{key:'log',icon:<CheckOutlined/>,label:'Ghi nhận đã liên hệ',onClick:()=>newTask({type:'CONTACT',status:'DONE'})},{key:'complaint',icon:<SolutionOutlined/>,label:'Ghi nhận phản ánh',onClick:()=>newTask({type:'COMPLAINT',status:'TODO'})}]};
 const info=[['Họ và tên',p.full_name],['E-mail',p.email],['Số điện thoại',p.phone],['Địa chỉ mặc định',p.default_address],['Số địa chỉ đã lưu',p.address_count],['Ngày đăng ký',dateTime(p.created_at)],['Đăng nhập gần nhất',p.last_login&&`${dateTime(p.last_login)} (${daysAgo(p.last_login)})`],
  ['Phân hạng khách hàng',profile&&<span>{p.tier}{p.next_tier&&<small className="cp-hint">Còn {money(p.next_tier.remaining)} để lên {p.next_tier.name}</small>}</span>],['Tổng chi tiêu',profile&&money(s.total_spent)],['Số đơn thành công',profile&&`${s.orders}${s.cancelled?` (đã hủy ${s.cancelled})`:''}`],['Giá trị đơn trung bình',s.orders?money(s.average_order):null],['Đơn đầu tiên',date(s.first_order_at)],['Đơn gần nhất',s.last_order_at&&`${date(s.last_order_at)} (${daysAgo(s.last_order_at)})`],
  ['Danh mục quan tâm',p.interests?.length?<Space size={[4,4]} wrap>{p.interests.map(i=><Tag key={i.category}>{i.category} · {i.quantity}</Tag>)}</Space>:null],['Phiên chat với AI',profile&&s.chat_sessions]];
 const tabs=[{key:'events',label:'Event'},{key:'tasks',label:<Badge count={s.open_tasks||0} size="small" offset={[8,-2]}>Công việc</Badge>},{key:'notes',label:`Ghi chú${s.notes?` (${s.notes})`:''}`},{key:'orders',label:'Lịch sử giao dịch'},{key:'addresses',label:'Sổ địa chỉ'}];
 return <div className="customer-profile">
  <aside className="cp-side">
   <Button type="link" className="cp-back" icon={<ArrowLeftOutlined/>} onClick={onBack}>Quay lại danh sách</Button>
   <div className="cp-identity"><Avatar size={64} src={p.avatar_url||undefined} icon={<UserOutlined/>}/><div><Typography.Title level={4}>{p.full_name}</Typography.Title>
    <Space size={8}><Dropdown menu={contact} trigger={['click']}><Button type="primary">Liên hệ <CaretDownOutlined/></Button></Dropdown><Tooltip title="Thêm ghi chú"><Button icon={<FileTextOutlined/>} aria-label="Thêm ghi chú" onClick={()=>{setFocusNote(true);setTab('notes')}}/></Tooltip><Tooltip title="Tạo công việc"><Button icon={<ScheduleOutlined/>} aria-label="Tạo công việc" onClick={()=>newTask({})}/></Tooltip><Dropdown trigger={['click']} menu={{items:[{key:'reload',icon:<ReloadOutlined/>,label:'Làm mới dữ liệu',onClick:changed}]}}><Button icon={<MoreOutlined/>} aria-label="Thêm thao tác"/></Dropdown></Space></div></div>
   <div className="cp-segment"><Typography.Text type="secondary">Phân khúc</Typography.Text><div>{profile?<><Tag color={TIER_COLOR[p.tier]}>{p.tier}</Tag><Tag color={s.orders?'green':'default'}>{s.orders?`Đã mua ${s.orders} đơn`:'Chưa mua hàng'}</Tag>{s.last_order_at&&<Tag color={(Date.now()-new Date(s.last_order_at))/864e5>90?'orange':'cyan'}>Mua gần nhất {daysAgo(s.last_order_at)}</Tag>}{s.open_tasks>0&&<Tag color="red" className="cp-clickable" onClick={()=>setTab('tasks')}>{s.open_tasks} việc cần làm</Tag>}{p.active===false&&<Tag>Tài khoản bị khóa</Tag>}</>:<Spin size="small"/>}</div><Button type="text" size="small" icon={<ArrowRightOutlined/>} aria-label="Xem lịch sử giao dịch" onClick={()=>setTab('orders')}/></div>
   <div className="cp-info-head"><Typography.Title level={5}>Thông tin Profile</Typography.Title><Tooltip title="Làm mới"><Button size="small" icon={<ReloadOutlined/>} aria-label="Làm mới thông tin" onClick={changed}/></Tooltip></div>
   {error?<Typography.Text type="danger">{error}</Typography.Text>:<dl className="cp-info">{info.map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v===null||v===undefined||v===''?empty:v}</dd></React.Fragment>)}</dl>}
  </aside>
  <section className="cp-main"><Tabs activeKey={tab} onChange={k=>{setTab(k);setFocusNote(false)}} items={tabs}/>
   <div className="cp-tab-body">{tab==='events'?<EventsTab base={base} reloadKey={reloadKey} openOrders={()=>setTab('orders')}/>:tab==='tasks'?<TasksTab base={base} reloadKey={reloadKey} onChanged={loadProfile} composer={composer} setComposer={setComposer}/>:tab==='notes'?<NotesTab base={base} reloadKey={reloadKey} onChanged={loadProfile} focus={focusNote}/>:tab==='orders'?<OrdersTab base={base} reloadKey={reloadKey} profile={profile}/>:<AddressTab base={base} onChanged={loadProfile}/>}</div>
  </section>
 </div>}
