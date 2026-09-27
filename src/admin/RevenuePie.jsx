import React from 'react';
import {Empty} from 'antd';
const colors=['#1768f2','#19a98c','#f5a623','#9061df','#ef637d','#13a8c7','#718096','#b7791f'];
const money=value=>Number(value).toLocaleString('vi-VN')+' ₫';
export default function RevenuePie({items,title}){
 const slices=items.filter(item=>Number.isFinite(item.value)&&item.value>0);
 const total=slices.reduce((sum,item)=>sum+item.value,0);
 if(!total)return <Empty description="Chưa có doanh thu trong kỳ"/>;
 let angle=-Math.PI/2;
 return <div className="report-pie-layout">
  <svg className="report-pie" viewBox="0 0 240 240" role="img" aria-label={`${title}: ${money(total)}`}>
   {slices.map((item,index)=>{
    const start=angle;
    angle+=item.value/total*Math.PI*2;
    const label=`${item.label}: ${money(item.value)} (${(item.value/total*100).toLocaleString('vi-VN',{maximumFractionDigits:1})}%)`;
    const props={fill:colors[index%colors.length],stroke:'#fff',strokeWidth:2,tabIndex:0,'aria-label':label};
    return slices.length===1?<circle key={item.label} cx="120" cy="120" r="108" {...props}><title>{label}</title></circle>:<path key={item.label} d={`M120 120 L${120+108*Math.cos(start)} ${120+108*Math.sin(start)} A108 108 0 ${angle-start>Math.PI?1:0} 1 ${120+108*Math.cos(angle)} ${120+108*Math.sin(angle)} Z`} {...props}><title>{label}</title></path>;
   })}
  </svg>
  <div className="report-pie-details"><p className="report-pie-total">Tổng doanh thu <strong>{money(total)}</strong></p><ul className="report-pie-legend">{slices.map((item,index)=><li key={item.label}><i style={{background:colors[index%colors.length]}}/><span>{item.label}<small>{money(item.value)}</small></span><b>{(item.value/total*100).toLocaleString('vi-VN',{maximumFractionDigits:1})}%</b></li>)}</ul></div>
 </div>;
}