import {describe,it,expect} from 'vitest';
import {defaults,decodeConfig,putConfig,apiQuery} from './stockExplorerModel';
describe('independent stock query context',()=>{
 it('starts Beach Tennis, all item kinds, type grouping',()=>{const c=defaults(true);expect(c.modality_ids).toEqual(['bt']);expect(c.item_kind_ids).toEqual([]);expect(c.group_by).toEqual(['item_kind']);});
 it('does not impose commercial filters on stock-only access',()=>{const c=defaults(false);expect(c.modality_ids).toEqual([]);expect(c.group_by).toEqual([]);});
 it('explicit empty URL overrides personal selection',()=>{expect(decodeConfig(new URLSearchParams('modality_ids=&group_by='),'',defaults(true)).modality_ids).toEqual([]);});
 it('roundtrips all choices and page zero without null',()=>{const c={...defaults(true),item_kind_ids:['type:1','type:5:BALL','type:8'],group_by:['model'],offset:0};const p=putConfig(new URLSearchParams(),'stock_',c);expect(decodeConfig(p,'stock_',defaults(true))).toEqual(c);});
 it('repeated API IDs express OR, not comma literal',()=>{const c={...defaults(true),item_kind_ids:['type:1','type:5:BALL']};expect(apiQuery(c).getAll('item_kind_ids')).toEqual(c.item_kind_ids);});
 it('explicit no position restriction includes every supported regime',()=>{expect(apiQuery({...defaults(true),position_ids:[]}).getAll('position_ids')).toEqual(['DOMESTIC','BONDED','QUARANTINE']);});
 it('group and measures do not modify filter values',()=>{const c={...defaults(true),item_kind_ids:['a','b'],model_ids:['m']};const changed={...c,group_by:['model'],measures:['sale']};for(const k of ['modality_ids','item_kind_ids','model_ids','position_ids','q'] as const)expect(changed[k]).toEqual(c[k]);});
});
