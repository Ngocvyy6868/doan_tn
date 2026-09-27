import test from 'node:test';
import assert from 'node:assert/strict';
import {matchesPcFamily} from '../src/lib/pc-products.mjs';
test('PC tabs classify CPU rather than graphics brand',()=>{
 const intel={cat:'PC Gaming',name:'PC Intel Core i5-14400F AMD Radeon RX 7600'};
 assert.equal(matchesPcFamily(intel,'intel'),true);
 assert.equal(matchesPcFamily(intel,'amd'),false);
 const amd={cat:'PC AMD',name:'Gaming PC',attributes:[{name:'CPU',value:'AMD Ryzen 5 7600'}]};
 assert.equal(matchesPcFamily(amd,'amd'),true);
 assert.equal(matchesPcFamily(amd,'ryzen 5'),true);
 assert.equal(matchesPcFamily({...amd,name:'Intel graphics PC'},'intel'),false);
 assert.equal(matchesPcFamily({...amd,cat:'CPU'},'amd'),false);
 assert.equal(matchesPcFamily({...amd,active:false},'all'),false);
 assert.equal(matchesPcFamily({cat:'PC Intel',name:'Office PC'},'intel'),true);
});
