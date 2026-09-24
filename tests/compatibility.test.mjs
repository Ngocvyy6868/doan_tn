import test from 'node:test';
import assert from 'node:assert/strict';
import {checkCompatibility} from '../src/compatibility.mjs';
const rule={name:'Socket',source_category:'CPU',source_attribute:'Socket',target_category:'Mainboard',target_attribute:'Socket',operator:'equal',active:true};
const products=(left,right)=>[{cat:'CPU',name:'CPU',attributes:[{name:'Socket',value:left}]},{cat:'Mainboard',name:'Board',attributes:[{name:'Socket',value:right}]}];
test('matching and mismatching sockets',()=>{
 assert.equal(checkCompatibility(products(' AM5 ','am5'),[rule])[0].status,'pass');
 assert.equal(checkCompatibility(products('AM5','LGA1700'),[rule])[0].status,'fail');
});
test('missing attributes and incomplete pairs',()=>{
 assert.equal(checkCompatibility(products('AM5',''),[rule])[0].status,'unknown');
 assert.deepEqual(checkCompatibility(products('AM5','AM5').slice(0,1),[rule]),[]);
 assert.deepEqual(checkCompatibility(products('AM5','AM5'),[{...rule,active:false}]),[]);
});
test('supported lists and numeric limits',()=>{
 assert.equal(checkCompatibility(products('DDR5','DDR4, DDR5'),[{...rule,operator:'overlap'}])[0].status,'pass');
 assert.equal(checkCompatibility(products('850','750'),[{...rule,operator:'gte'}])[0].status,'pass');
 assert.equal(checkCompatibility(products('850','750'),[{...rule,operator:'lte'}])[0].status,'fail');
 const items=products('850','750');items[0].attributes[0].unit='W';
 assert.equal(checkCompatibility(items,[{...rule,operator:'gte'}])[0].status,'unknown');
 assert.equal(checkCompatibility(products('unknown','750'),[{...rule,operator:'gte'}])[0].status,'unknown');
});
