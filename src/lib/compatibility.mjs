const normalize=value=>String(value??'').trim().toLocaleLowerCase('vi');
const attribute=(product,name)=>product.attributes?.find(item=>normalize(item.name)===normalize(name));
const tokens=value=>(Array.isArray(value)?value:String(value??'').split(/[,;\n]/)).map(normalize).filter(Boolean);
export function checkCompatibility(products,rules){
 return rules.filter(rule=>rule.active).flatMap(rule=>{
  const source=products.find(p=>p.cat===rule.source_category),target=products.find(p=>p.cat===rule.target_category);
  if(!source||!target)return [];
  const left=attribute(source,rule.source_attribute),right=attribute(target,rule.target_attribute);
  const result={rule:rule.name,pair:`${source.name} / ${target.name}`};
  if(!tokens(left?.value).length||!tokens(right?.value).length)return [{...result,status:'unknown',message:'Thiếu thông số để kiểm tra.'}];
  let valid;
  if(rule.operator==='equal')valid=normalize(left.value)===normalize(right.value);
  else if(rule.operator==='overlap')valid=tokens(left.value).some(value=>tokens(right.value).includes(value));
  else if(rule.operator==='gte'||rule.operator==='lte'){
   const a=Number(left.value),b=Number(right.value);
   if(!Number.isFinite(a)||!Number.isFinite(b)||normalize(left.unit)!==normalize(right.unit))return [{...result,status:'unknown',message:'Thông số phải là số và cùng đơn vị.'}];
   valid=rule.operator==='gte'?a>=b:a<=b;
  }else return [{...result,status:'unknown',message:'Phép so sánh không được hỗ trợ.'}];
  return [{...result,status:valid?'pass':'fail',message:`${rule.source_attribute}: ${left.value} ${left.unit||''} / ${rule.target_attribute}: ${right.value} ${right.unit||''}`}];
 });
}

const POWER_ATTRIBUTE='Công suất',POWER_MARGIN=1.2;
const wattageOf=product=>{const value=Number(attribute(product,POWER_ATTRIBUTE)?.value);return Number.isFinite(value)?value:0};

export function estimatePsuRequirement(products){
 const psu=products.find(p=>p.cat==='Nguồn'),others=products.filter(p=>p.cat!=='Nguồn');
 const sum=others.reduce((total,p)=>total+wattageOf(p),0),required=Math.ceil(sum*POWER_MARGIN);
 if(!sum)return{sum,required:0,psuWattage:psu?wattageOf(psu):null,status:'empty'};
 if(!psu)return{sum,required,psuWattage:null,status:'suggest'};
 const psuWattage=wattageOf(psu);
 if(!psuWattage)return{sum,required,psuWattage:null,status:'unknown'};
 return{sum,required,psuWattage,status:psuWattage>=required?'pass':'fail'};
}
