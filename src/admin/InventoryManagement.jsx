import React,{useEffect,useMemo,useState} from 'react';
import {App,Breadcrumb,Button,Card,Empty,Form,Image,Input,InputNumber,Modal,Popconfirm,Radio,Select,Space,Switch,Table,Tabs,Tag,Tooltip,Typography} from 'antd';
import {DeleteOutlined,EditOutlined,EnvironmentOutlined,ImportOutlined,PlusOutlined,SearchOutlined} from '@ant-design/icons';
const api=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000/api';
async function request(path,method='GET',body){
 const r=await fetch(api+path,{method,credentials:'include',...(body?{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(r.status===403?'Vui lòng đăng nhập bằng tài khoản quản trị.':data.message||'Không thể xử lý yêu cầu.');
 return data;
}

function WarehouseModal({open,warehouse,onClose,onSaved}){
 const {message}=App.useApp(),[form]=Form.useForm(),[saving,setSaving]=useState(false);
 useEffect(()=>{if(open){form.resetFields();form.setFieldsValue(warehouse||{active:true})}},[open,warehouse,form]);
 const submit=async values=>{setSaving(true);try{const data=await request(warehouse?`/admin/warehouses/${warehouse.id}/`:'/admin/warehouses/',warehouse?'PATCH':'POST',{...values,code:values.code.trim().toUpperCase(),address:values.address.trim()});onSaved(data.warehouse);message.success(warehouse?'Đã cập nhật kho.':'Đã thêm kho.');onClose()}catch(e){message.error(e.message)}finally{setSaving(false)}};
 return <Modal title={warehouse?`Sửa kho ${warehouse.code}`:'Thêm kho'} open={open} onCancel={onClose} onOk={()=>form.submit()} okText={warehouse?'Lưu':'Thêm kho'} cancelText="Hủy" confirmLoading={saving} destroyOnHidden>
  <Form form={form} layout="vertical" onFinish={submit} requiredMark="optional">
   <Form.Item label="Mã kho" name="code" normalize={v=>(v||'').toUpperCase()} extra="Ví dụ: HN01, HCM-Q1. Gồm 2–20 ký tự chữ in hoa, số, “-” hoặc “_”."
    rules={[{required:true,message:'Nhập mã kho'},{pattern:/^[A-Z0-9][A-Z0-9_-]{1,19}$/,message:'Mã kho chưa đúng định dạng'}]}><Input maxLength={20} placeholder="HN01"/></Form.Item>
   <Form.Item label="Địa chỉ" name="address" rules={[{required:true,whitespace:true,message:'Nhập địa chỉ kho'},{min:5,message:'Địa chỉ quá ngắn'}]}><Input.TextArea maxLength={255} showCount rows={3} placeholder="Số nhà, đường, phường/xã, tỉnh/thành phố"/></Form.Item>
   {warehouse&&<Form.Item label="Đang hoạt động" name="active" valuePropName="checked" extra="Kho ngừng hoạt động không được tính vào tồn kho bán và không hiển thị cho khách."><Switch/></Form.Item>}
  </Form>
 </Modal>;
}

function StockModal({open,product,warehouses,stocks,onClose,onSaved}){
 const {message}=App.useApp(),[form]=Form.useForm(),[saving,setSaving]=useState(false);
 const mode=Form.useWatch('mode',form),warehouseId=Form.useWatch('warehouse_id',form);
 const current=stocks?.[String(warehouseId)]||0;
 useEffect(()=>{if(open){form.resetFields();form.setFieldsValue({mode:'add',warehouse_id:warehouses.find(w=>w.active)?.id,quantity:null})}},[open,form,warehouses]);
 const submit=async values=>{setSaving(true);try{const data=await request('/admin/inventory/','POST',{product_id:product.id,warehouse_id:values.warehouse_id,quantity:values.quantity,mode:values.mode});onSaved(data);message.success('Đã cập nhật tồn kho.');onClose()}catch(e){message.error(e.message)}finally{setSaving(false)}};
 return <Modal title="Cập nhật tồn kho" open={open} onCancel={onClose} onOk={()=>form.submit()} okText="Lưu" cancelText="Hủy" confirmLoading={saving} destroyOnHidden>
  {product&&<div className="inventory-modal-product">{product.img&&<img src={product.img} alt=""/>}<div><b>{product.name}</b><small>{product.sku||product.id}</small></div></div>}
  <Form form={form} layout="vertical" onFinish={submit}>
   <Form.Item label="Kho" name="warehouse_id" rules={[{required:true,message:'Chọn kho'}]}>
    <Select options={warehouses.map(w=>({value:w.id,label:`${w.code} — ${w.address}${w.active?'':' (ngừng hoạt động)'}`}))} placeholder="Chọn kho"/>
   </Form.Item>
   <Form.Item name="mode" label="Thao tác"><Radio.Group optionType="button" buttonStyle="solid" options={[{value:'add',label:'Nhập thêm'},{value:'set',label:'Đặt số lượng'}]}/></Form.Item>
   <Form.Item label={mode==='set'?'Số lượng mới':'Số lượng nhập thêm'} name="quantity" extra={warehouseId?`Hiện có ${current} sản phẩm tại kho này.${mode==='add'?' Nhập số âm để xuất kho.':''}`:null}
    rules={[{required:true,message:'Nhập số lượng'},{validator:(_,v)=>v==null||(mode==='set'?v>=0:v!==0&&current+v>=0)?Promise.resolve():Promise.reject(Error(mode==='set'?'Số lượng không được âm':v===0?'Số lượng phải khác 0':`Kho chỉ còn ${current} sản phẩm`))}]}>
    <InputNumber precision={0} min={mode==='set'?0:-1000000} max={1000000} style={{width:'100%'}} placeholder="0"/>
   </Form.Item>
  </Form>
 </Modal>;
}

export default function InventoryManagement({products,onStock}){
 const {message}=App.useApp();
 const [warehouses,setWarehouses]=useState([]),[stocks,setStocks]=useState({}),[loading,setLoading]=useState(true);
 const [warehouseModal,setWarehouseModal]=useState({open:false,warehouse:null}),[stockProduct,setStockProduct]=useState(null);
 const [query,setQuery]=useState(''),[filter,setFilter]=useState('all');
 const load=()=>Promise.all([request('/admin/warehouses/'),request('/admin/inventory/')]).then(([w,s])=>{setWarehouses(w.results);setStocks(s.results)}).catch(e=>message.error(e.message)).finally(()=>setLoading(false));
 useEffect(()=>{load()},[]);// eslint-disable-line react-hooks/exhaustive-deps
 const reloadWarehouses=()=>request('/admin/warehouses/').then(d=>setWarehouses(d.results)).catch(()=>{});
 const removeWarehouse=async w=>{try{await request(`/admin/warehouses/${w.id}/`,'DELETE');setWarehouses(c=>c.filter(x=>x.id!==w.id));setStocks(c=>Object.fromEntries(Object.entries(c).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).filter(([id])=>id!==String(w.id)))])));message.success(`Đã xóa kho ${w.code}.`)}catch(e){message.error(e.message)}};
 const stockSaved=data=>{setStocks(c=>({...c,[data.product_id]:data.stocks}));onStock?.(data.product_id,data.stock);reloadWarehouses()};
 const rows=useMemo(()=>{const q=query.trim().toLowerCase();return products.filter(p=>{
  if(q&&!`${p.name} ${p.sku||''} ${p.id}`.toLowerCase().includes(q))return false;
  const total=Object.values(stocks[p.id]||{}).reduce((s,n)=>s+n,0);
  return filter==='all'||(filter==='unassigned'?!stocks[p.id]:filter==='out'?Boolean(stocks[p.id])&&total===0:true)})},[products,stocks,query,filter]);

 const warehouseColumns=[
  {title:'MÃ KHO',dataIndex:'code',width:140,render:v=><Typography.Text strong copyable>{v}</Typography.Text>},
  {title:'ĐỊA CHỈ',dataIndex:'address',render:v=><Space><EnvironmentOutlined style={{color:'#1768f2'}}/>{v}</Space>},
  {title:'TỔNG TỒN',dataIndex:'total_quantity',width:120,align:'right',render:v=>v.toLocaleString('vi-VN')},
  {title:'TRẠNG THÁI',dataIndex:'active',width:150,render:v=><Tag color={v?'green':'default'}>{v?'Đang hoạt động':'Ngừng hoạt động'}</Tag>},
  {title:'',width:110,align:'right',render:(_,w)=><Space><Tooltip title="Sửa"><Button type="text" icon={<EditOutlined/>} onClick={()=>setWarehouseModal({open:true,warehouse:w})}/></Tooltip>
   <Popconfirm title={`Xóa kho ${w.code}?`} description="Chỉ xóa được khi kho không còn hàng." okText="Xóa" cancelText="Hủy" okButtonProps={{danger:true}} onConfirm={()=>removeWarehouse(w)}><Tooltip title="Xóa"><Button type="text" danger icon={<DeleteOutlined/>}/></Tooltip></Popconfirm></Space>}];

 const stockColumns=[
  {title:'SẢN PHẨM',fixed:'left',width:320,render:(_,p)=><div className="inventory-product">{p.img?<Image src={p.img} width={44} height={44} preview={false} style={{objectFit:'contain'}}/>:<span className="inventory-noimg"/>}<div><b>{p.name}</b><small>{p.sku||p.id}{p.active===false&&' · Đang ẩn'}</small></div></div>},
  ...warehouses.map(w=>({title:<Tooltip title={w.address}><span className={w.active?'':'inventory-inactive'}>{w.code}</span></Tooltip>,key:w.id,width:110,align:'right',
   render:(_,p)=>{const n=stocks[p.id]?.[String(w.id)];return n==null?<Typography.Text type="secondary">—</Typography.Text>:<span className={w.active?'':'inventory-inactive'}>{n.toLocaleString('vi-VN')}</span>}})),
  {title:'TỔNG BÁN ĐƯỢC',width:140,align:'right',render:(_,p)=>{if(!stocks[p.id])return <Tooltip title="Chưa phân kho; đang dùng tồn kho nhập tay trong form sản phẩm."><Tag>Chưa phân kho · {p.stock??0}</Tag></Tooltip>;const total=warehouses.filter(w=>w.active).reduce((s,w)=>s+(stocks[p.id][String(w.id)]||0),0);return <Tag color={total===0?'red':total<=5?'orange':'green'}>{total.toLocaleString('vi-VN')}</Tag>}},
  {title:'',fixed:'right',width:130,align:'right',render:(_,p)=><Button icon={<ImportOutlined/>} disabled={!warehouses.length} onClick={()=>setStockProduct(p)}>Nhập kho</Button>}];

 return <>
  <Breadcrumb items={[{title:'Kho hàng'}]}/>
  <div className="content-title"><div><Typography.Title level={2}>Quản lý kho hàng</Typography.Title><Typography.Text type="secondary">Tạo kho/cửa hàng và cập nhật số lượng từng sản phẩm tại mỗi kho. Tồn kho bán được bằng tổng các kho đang hoạt động.</Typography.Text></div>
   <Button type="primary" size="large" icon={<PlusOutlined/>} onClick={()=>setWarehouseModal({open:true,warehouse:null})}>Thêm kho</Button></div>
  <Card><Tabs items={[
   {key:'stock',label:'Tồn kho theo sản phẩm',children:warehouses.length||loading?<>
    <Space wrap style={{marginBottom:16}}><Input prefix={<SearchOutlined/>} allowClear placeholder="Tìm tên, SKU" value={query} onChange={e=>setQuery(e.target.value)} style={{width:300}}/>
     <Select value={filter} onChange={setFilter} style={{width:200}} options={[{value:'all',label:'Tất cả sản phẩm'},{value:'unassigned',label:'Chưa phân kho'},{value:'out',label:'Hết hàng tại mọi kho'}]}/></Space>
    <Table rowKey="id" loading={loading} dataSource={rows} columns={stockColumns} scroll={{x:640+warehouses.length*110}} pagination={{pageSize:10,showSizeChanger:false}}/></>
    :<Empty description="Chưa có kho nào. Hãy thêm kho trước khi nhập số lượng."><Button type="primary" icon={<PlusOutlined/>} onClick={()=>setWarehouseModal({open:true,warehouse:null})}>Thêm kho</Button></Empty>},
   {key:'warehouses',label:`Danh sách kho (${warehouses.length})`,children:<Table rowKey="id" loading={loading} dataSource={warehouses} columns={warehouseColumns} pagination={false} scroll={{x:720}}/>}]}/></Card>
  <WarehouseModal open={warehouseModal.open} warehouse={warehouseModal.warehouse} onClose={()=>setWarehouseModal({open:false,warehouse:null})}
   onSaved={w=>{setWarehouses(c=>(c.some(x=>x.id===w.id)?c.map(x=>x.id===w.id?w:x):[...c,w]).sort((a,b)=>a.code.localeCompare(b.code)));if(warehouseModal.warehouse&&warehouseModal.warehouse.active!==w.active)load()}}/>
  <StockModal open={Boolean(stockProduct)} product={stockProduct} warehouses={warehouses} stocks={stockProduct?stocks[stockProduct.id]:null} onClose={()=>setStockProduct(null)} onSaved={stockSaved}/>
 </>;
}
