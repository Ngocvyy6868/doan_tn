import React from 'react';
import {Avatar,Card,Descriptions,List,Tag,Typography} from 'antd';
const money=value=>Number(value||0).toLocaleString('vi-VN')+' ₫';
export default function AdminOrderDetails({order}){
 const recipient=order.recipient||{},totals=order.totals||{};
 return <div className="admin-order-details"><div className="admin-order-info"><Card size="small" title="Thông tin giao hàng"><Descriptions column={1} size="small" items={[
  {key:'name',label:'Người nhận',children:recipient.name||'—'},
  {key:'phone',label:'Số điện thoại',children:recipient.phone||'—'},
  {key:'address',label:'Địa chỉ',children:[recipient.address,recipient.province].filter(Boolean).join(', ')||'—'},
  {key:'shipping',label:'Giao hàng',children:({standard:'Giao hàng tiêu chuẩn',express:'Giao hàng nhanh'})[order.shipping_method]||order.shipping_method||'—'},
 ]}/></Card><Card size="small" title="Thông tin thanh toán"><Descriptions column={1} size="small" items={[
  {key:'method',label:'Phương thức',children:({COD:'Thanh toán khi nhận hàng (COD)',SANDBOX:'Thanh toán điện tử Sandbox'})[order.payment_method]||order.payment_method||'—'},
  {key:'status',label:'Thanh toán',children:<Tag color={order.payment_status==='PAID'?'success':'warning'}>{({PAID:'Đã thanh toán',UNPAID:'Chưa thanh toán'})[order.payment_status]||order.payment_status||'—'}</Tag>},
  {key:'subtotal',label:'Tiền hàng',children:money(totals.subtotal)},
  {key:'shipping',label:'Phí giao hàng',children:money(totals.shipping)},
  {key:'total',label:'Tổng tiền',children:<Typography.Text strong className="admin-order-total">{money(totals.grand_total)}</Typography.Text>},
 ]}/></Card></div><List header={<Typography.Text strong>Sản phẩm trong đơn</Typography.Text>} bordered size="small" dataSource={order.items||[]} renderItem={item=><List.Item actions={[<Typography.Text key="quantity">Số lượng: {item.quantity}</Typography.Text>,<Typography.Text strong key="total">{money(item.total)}</Typography.Text>]}><List.Item.Meta avatar={<Avatar shape="square" src={item.image}/>} title={item.name} description={`SKU: ${item.sku} • ${money(item.price)}/sản phẩm`}/></List.Item>}/></div>;
}
