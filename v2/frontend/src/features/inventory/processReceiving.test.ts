import { afterEach,it,expect,vi } from "vitest";
import { readProcessReceiving,type ReceivingRow } from "./processReceiving";
afterEach(()=>vi.unstubAllGlobals());
const rows=Array.from({length:205},(_,id)=>({item_id:id+1,process_id:id%2?2:1,process_code:id%2?"IMP-10":"IMP-1"})) as ReceivingRow[];
it("selects exact IDs after every page, including similar codes and later rows",async()=>{
 const fetcher=vi.fn(async(url:string)=>{const offset=Number(new URL(url,"http://test").searchParams.get("offset"));return {ok:true,json:async()=>({rows:rows.slice(offset,offset+100),total:rows.length,offset,limit:100})};});vi.stubGlobal("fetch",fetcher);
 const result=await readProcessReceiving(1);expect(result).toHaveLength(103);expect(result.every(row=>row.process_id===1)).toBe(true);expect(result.at(-1)?.item_id).toBe(205);expect(fetcher).toHaveBeenCalledTimes(3);expect(fetcher.mock.calls.every(([url])=>!url.includes("q="))).toBe(true);
});
it("rejects incomplete pagination instead of reporting a partial set as complete",async()=>{vi.stubGlobal("fetch",vi.fn(async()=>({ok:true,json:async()=>({rows:rows.slice(0,25),total:205,limit:100,offset:0})})));await expect(readProcessReceiving(1)).rejects.toThrow("incompleta");});
it("rejects shifting totals and duplicate page entries",async()=>{vi.stubGlobal("fetch",vi.fn(async()=>({ok:true,json:async()=>({rows:rows.slice(0,100),total:200,limit:100,offset:0})})));await expect(readProcessReceiving(1)).rejects.toThrow("mudou");});
it("preserves a source error",async()=>{vi.stubGlobal("fetch",vi.fn(async()=>({ok:false,status:403})));await expect(readProcessReceiving(1)).rejects.toThrow("acesso");});
it("does not start a broad query for an invalid ID",async()=>{const fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);await expect(readProcessReceiving(0)).rejects.toThrow("inválida");expect(fetcher).not.toHaveBeenCalled();});
it("accepts exactly 10000 distinct rows and refuses 10001 explicitly",async()=>{
 const tenThousand=Array.from({length:10000},(_,i)=>({item_id:i+1,process_id:i===9999?77:2}));
 const fetcher=vi.fn(async(url:string)=>{const offset=Number(new URL(url,"http://test").searchParams.get("offset"));return {ok:true,json:async()=>({rows:tenThousand.slice(offset,offset+100),total:10000,offset,limit:100})};});
 vi.stubGlobal("fetch",fetcher);expect((await readProcessReceiving(77)).map(row=>row.item_id)).toEqual([10000]);expect(fetcher).toHaveBeenCalledTimes(100);
 const oversized=vi.fn(async()=>({ok:true,json:async()=>({rows:tenThousand.slice(0,100),total:10001,offset:0,limit:100})}));
 vi.stubGlobal("fetch",oversized);await expect(readProcessReceiving(77)).rejects.toThrow("limite da consulta contextual");expect(oversized).toHaveBeenCalledTimes(1);
});
