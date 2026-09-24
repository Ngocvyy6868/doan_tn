import test from 'node:test';
import assert from 'node:assert/strict';
import {isCompatibleCandidate,productWattage} from '../src/lib/compatibility.mjs';
const rule={active:true,name:'Socket',source_category:'CPU',target_category:'Mainboard',source_attribute:'Socket',target_attribute:'Socket',operator:'equal'};
const item=(cat,socket,power)=>({cat,name:cat,attributes:[{name:'Socket',value:socket},{name:'Công suất',value:power}]});
test('filter accepts matching sockets and hides mismatches or missing data',()=>{
 const selected=[item('CPU','AM5',100)];
 assert.equal(isCompatibleCandidate(item('Mainboard','AM5',50),selected,[rule]),true);
 assert.equal(isCompatibleCandidate(item('Mainboard','AM4',50),selected,[rule]),false);
 assert.equal(isCompatibleCandidate(item('Mainboard','',50),selected,[rule]),false);
});
test('replacement removes previous product in same category',()=>{
 assert.equal(isCompatibleCandidate(item('CPU','AM5',100),[item('CPU','AM4',100),item('Mainboard','AM5',50)],[rule]),true);
});
test('filter checks RAM quantities and PSU reserve',()=>{
 const board={...item('Mainboard','',50),attributes:[{name:'Số khe RAM',value:'2'}]};
 assert.equal(isCompatibleCandidate(item('RAM','',10),[board,{...item('RAM','',10),quantity:3}],[]),false);
 assert.equal(isCompatibleCandidate(item('Nguồn','',100),[item('CPU','',100)],[]),false);
 assert.equal(isCompatibleCandidate(item('Nguồn','',120),[item('CPU','',100)],[]),true);
});
test('power distinguishes unknown from genuine zero',()=>{
 assert.equal(productWattage(item('Case','','')),null);
 assert.equal(productWattage(item('Case','',0)),0);
 assert.equal(productWattage(item('CPU','',-20)),null);
});
