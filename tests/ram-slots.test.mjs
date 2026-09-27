import test from 'node:test';
import assert from 'node:assert/strict';
import {checkRamSlots,estimatePsuRequirement} from '../src/lib/compatibility.mjs';
const board=value=>({cat:'Mainboard',name:'Board',attributes:[{name:'Số khe RAM',value}]});
const ram=(quantity,value='')=>({cat:'RAM',name:'RAM',quantity,attributes:[{name:'Số thanh RAM',value},{name:'TDP',value:'10'}]});
test('RAM quantity at capacity passes; above capacity warns',()=>{
 assert.equal(checkRamSlots([board('2'),ram(2)])[0].status,'pass');
 assert.equal(checkRamSlots([board('2'),ram(3)])[0].status,'fail');
});
test('quantity counts sticks directly and ignores the removed attribute',()=>{
 assert.equal(checkRamSlots([board('4'),ram(4,'2')])[0].status,'pass');
 assert.equal(checkRamSlots([board('4'),ram(5,'2')])[0].status,'fail');
 assert.equal(checkRamSlots([board('4'),ram(3),ram(2)])[0].status,'fail');
});
test('missing and invalid specifications are unknown; incomplete builds are skipped',()=>{
 for(const value of ['', 'DDR5', '0', '-1', '2.5'])assert.equal(checkRamSlots([board(value),ram(1)])[0].status,'unknown');
 assert.equal(checkRamSlots([board('4'),ram(1,'invalid')])[0].status,'pass');
 assert.equal(checkRamSlots([board('4'),ram(0)])[0].status,'unknown');
 assert.deepEqual(checkRamSlots([ram(1)]),[]);
 assert.deepEqual(checkRamSlots([board('4')]),[]);
});
test('power estimate includes RAM quantity',()=>{
 assert.equal(estimatePsuRequirement([ram(3)]).sum,30);
 assert.equal(estimatePsuRequirement([ram(3)]).required,36);
});
