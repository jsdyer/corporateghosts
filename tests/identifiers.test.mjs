import test from 'node:test';
import assert from 'node:assert/strict';
import {parseIdentifier,businessSearchTerm,businessNumberFile,businessNumberMatches} from '../web/identifiers.mjs';
test('business numbers and program accounts normalize without becoming corporation IDs',()=>{
 for(const input of ['123456789','123 456 789','123-456-789','123456789RC0001','123 456 789 rt 0001']) assert.deepEqual(parseIdentifier(input),{type:'business',value:'123456789'});
 assert.deepEqual(parseIdentifier('1234567-8'),{type:'corporation',value:'12345678'});
 assert.deepEqual(parseIdentifier('123456789','corporation'),{type:'corporation',value:'123456789'});
 assert.throws(()=>parseIdentifier('BC1234567'));
 assert.throws(()=>parseIdentifier('123456789DROP'));
 assert.throws(()=>parseIdentifier('1234567','business'));
 assert.throws(()=>parseIdentifier('123456789','other'));
});
test('business-number searches preserve names and match canonical BN9',()=>{
 assert.equal(businessSearchTerm('123 456 789 RT0001'),'123456789');
 for(const q of ['Example Company','1234567','123456789 extra']) assert.equal(businessSearchTerm(q),null);
});
test('only the matching first-party prefix file can be loaded',()=>{
 const m={business_numbers:{version:1,prefix_length:3,shards:{'123':'business-numbers-123-abcdef0123456789.json.gz'}}};
 assert.equal(businessNumberFile(m,'123456789'),m.business_numbers.shards['123']);
 assert.equal(businessNumberFile(m,'987654321'),null);
 assert.throws(()=>businessNumberFile({},'123456789'));
 for(const file of ['https://example.com/data.json','../private.json','business-numbers-456-abcdef0123456789.json.gz']) assert.throws(()=>businessNumberFile({business_numbers:{version:1,prefix_length:3,shards:{123:file}}},'123456789'));
});
test('exact matches preserve ambiguity rather than guessing a corporation',()=>{
 const d={'123456789':['1007','2008','1007'],'123456788':['3009']};
 assert.deepEqual(businessNumberMatches(d,'123456789'),['1007','2008']);
 assert.deepEqual(businessNumberMatches(d,'123456780'),[]);
 for(const value of [[],[''],['not-a-number'],[123],null]) assert.throws(()=>businessNumberMatches({'123456789':value},'123456789'));
});
