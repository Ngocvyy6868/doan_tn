const normalize=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
export const isPcProduct=product=>/^(pc(?:\s+.*)?|may tinh bo|may bo)$/.test(normalize(product.cat));
function cpuText(product){
 const specs=(product.attributes||[]).filter(a=>/\b(cpu|processor|vi xu ly|bo xu ly)\b/.test(normalize(a.name))).map(a=>Array.isArray(a.value)?a.value.join(' '):a.value).filter(v=>String(v??'').trim());
 return normalize(specs.length?specs.join(' '):`${product.name||''} ${product.cat||''}`);
}
export function matchesPcFamily(product,family){
 if(!isPcProduct(product)||product.active===false)return false;
 if(family==='all')return true;
 const text=cpuText(product);
 const intel=/\b(intel|core\s*(?:ultra\s*)?[3579]|i[3579](?=\b|\d)|xeon|pentium|celeron)\b/.test(text);
 const amd=/\b(ryzen|threadripper|athlon|r[3579](?=\b|\d))\b/.test(text);
 if(family==='intel')return intel;
 if(family==='amd')return amd||(!intel&&/\bamd\b/.test(text));
 if(/^i[3579]$/.test(family))return new RegExp(`\\b${family}(?=\\b|\\d)`).test(text);
 const tier=family.match(/^ryzen ([3579])$/)?.[1];
 return !!tier&&new RegExp(`\\b(?:ryzen\\s*${tier}|r${tier})(?=\\b|\\d)`).test(text);
}
