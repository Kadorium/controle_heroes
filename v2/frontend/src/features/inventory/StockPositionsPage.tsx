import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { PdfViewerPanel } from "../ingestion/PdfViewerPanel";
import { regimes, number, money, kindLabel, statusLabel, useRead, type StockPosition, type CostSources, type ProductCost } from "./stockRead";

const detailKeys = ["product", "case", "version", "section", "doc", "sources_page"];
const componentLabel:Record<string,string> = {MERCADORIA:"Mercadoria", II:"Imposto de importação", IPI:"IPI", PIS:"PIS", COFINS:"Cofins", ICMS:"ICMS", EXPENSE_COSTING_OUTRAS:"Outras despesas", FRETE_INTERNACIONAL:"Frete internacional", FRETE_NACIONAL:"Frete nacional"};
export function StockPositionsPage({user}:{user:User}) {
  const [params,setParams] = useSearchParams(), location = useLocation(), navigate = useNavigate();
  const can = (p:string) => user.role==="admin" || user.permissions.includes(p);
  const productId=Number(params.get("product"))||0, caseId=Number(params.get("case"))||0, versionId=Number(params.get("version"))||0;
  const section=params.get("section"), docId=Number(params.get("doc"))||0;
  const offset=Math.max(0,Number(params.get("page"))||0)*25, sourcesOffset=Math.max(0,Number(params.get("sources_page"))||0)*25;
  const listQuery = new URLSearchParams({limit:"25",offset:String(offset),status:params.get("status")||"positive",sort:params.get("sort")||"name"});
  for(const key of ["q","regime","location_id"]) if(params.get(key)) listQuery.set(key,params.get(key)!);
  const list=useRead<StockPosition>(can("inventory:read") && !productId ? `/api/reporting/stock-positions?${listQuery}`:null);
  const [locations,setLocations]=useState<StockPosition["locations"]>([]);
  useEffect(()=>{if(list.data) setLocations(list.data.locations);},[list.data]);
  const item=useRead<StockPosition>(can("inventory:read") && productId ? `/api/reporting/stock-positions?product_id=${productId}&status=all`:null);
  const sources=useRead<CostSources>(can("costing:read") && productId ? `/api/costing/products/${productId}/sources?limit=25&offset=${caseId?0:sourcesOffset}${caseId?`&case_id=${caseId}`:""}`:null);
  const cost=useRead<ProductCost>(can("costing:read") && productId && versionId ? `/api/costing/products/${productId}/versions/${versionId}`:null);
  const row=item.data?.rows[0], selectedCase=sources.data?.rows.find(r=>r.case_id===caseId);
  const currentCost=cost.data && cost.data.case_id===caseId ? cost.data : null;
  const doc=currentCost?.components.flatMap(c=>c.documents).find(d=>d.id===docId);
  const heading=useRef<HTMLHeadingElement>(null);
  const contextKey=(search:string)=>`epic.stock.context:${search}`;
  function go(changes:Record<string,string|null>, replace=false) {
    sessionStorage.setItem(contextKey(location.search),JSON.stringify({scroll:window.scrollY,focus:(document.activeElement as HTMLElement)?.id}));
    const next=new URLSearchParams(params); Object.entries(changes).forEach(([k,v])=>v===null?next.delete(k):next.set(k,v));
    setParams(next,{replace,state:{stockParent:location.search}});
  }
  function back() {
    if(location.state?.stockParent != null) navigate(-1);
    else if(docId) go({doc:null}); else if(section) go({section:null}); else go(Object.fromEntries(detailKeys.map(k=>[k,null])));
  }
  useEffect(()=> {
    if(!productId) return;
    const handler=(e:KeyboardEvent)=> {if(e.key==="Escape" && !document.querySelector('[role="dialog"]')) {e.preventDefault();back();}};
    window.addEventListener("keydown",handler); return()=>window.removeEventListener("keydown",handler);
  });
  useEffect(()=> {
    const ready=productId ? !!row && (!versionId || !!currentCost) : !!list.data;
    if(!ready) return;
    const frame=requestAnimationFrame(()=> {
      const saved=sessionStorage.getItem(contextKey(location.search));
      if(saved) {try {const c=JSON.parse(saved); document.getElementById(c.focus)?.focus({preventScroll:true});window.scrollTo(0,c.scroll);} catch {heading.current?.focus();}}
      else if(productId) {heading.current?.focus({preventScroll:true});window.scrollTo(0,0);}
    });return()=>cancelAnimationFrame(frame);
  },[location.key,location.search,productId,versionId,row,currentCost,list.data]);
  const state=(r:{busy:boolean;error:string|null;retry:()=>void})=>r.busy?<p className="experience-status" role="status">Carregando…</p>:r.error?<div className="experience-error" role="alert">{r.error} <button onClick={r.retry}>Tentar novamente</button></div>:null;
  if(!can("inventory:read")) return <section className="experience-page"><h1>Estoque atual</h1><p>Seu acesso não permite consultar estoque.</p></section>;
  if(productId) return <section className="experience-page" data-testid="stock-product-context">
    <nav className="context-crumbs" aria-label="Caminho do produto"><button onClick={()=>go(Object.fromEntries(detailKeys.map(k=>[k,null])))}>Estoque atual</button><span>›</span><button onClick={()=>go({section:null,doc:null})}>{row?.sku||"Produto"}</button>{section && <><span>›</span><button onClick={()=>go({doc:null})}>Composição</button></>}{docId>0 && <span>› Documento</span>}</nav>
    <div className="experience-heading"><div><p className="eyebrow">{row?.sku} {docId ? "· Documento de origem" : section ? "· Composição do custo" : "· Posição atual"}</p><h1 ref={heading} tabIndex={-1}>{docId ? doc?.name||"Documento" : row?.name||"Produto"}</h1></div><button id="stock-context-back" onClick={back}>← Voltar</button></div>
    {state(item)}
    {item.data && !row && <p>Produto não encontrado.</p>}
    {row && !section && !docId && <>
      <dl className="experience-stats">{Object.entries(regimes).map(([k,label])=><div key={k}><dt>{label}</dt><dd>{number(row.quantities[k as keyof typeof regimes])} <small>{row.unit||"unidade não informada"}</small></dd></div>)}</dl>
      {row.balances.some(b=>Number(b.qty)!==0) && <p className="muted">{row.balances.filter(b=>Number(b.qty)!==0).map(b=>`${b.name} · ${number(b.qty)} ${row.unit||""}`).join(" / ")}</p>}
      <Link className="experience-link" to={`/inventory/movements?product_id=${productId}`} state={{stockReturn:location.pathname+location.search}}>Ver movimentos</Link>
      <section className="experience-cost"><div className="experience-cost-header"><h2>Custo por compra</h2>{selectedCase && <button onClick={()=>go({case:null,version:null})}>Escolher outra compra</button>}</div>
        {!can("costing:read") ? <p className="muted">Custo não disponível para este acesso. A posição de estoque permanece disponível.</p> : <>{state(sources)}
          {sources.data?.total===0 && <p className="muted">Nenhum custo vinculado a este produto.</p>}
          {sources.data && !selectedCase && <><p className="muted">Selecione a compra para consultar o custo e sua versão.</p>{sources.data.rows.map(c=><button className="experience-purchase" id={`purchase-${c.case_id}`} key={c.case_id} onClick={()=>go({case:String(c.case_id),version:c.current_published_id && c.versions.some(v=>v.id===c.current_published_id)?String(c.current_published_id):null})}><span><strong>{c.reference||c.code}</strong><br/>{c.versions[0]?.invoices.map(i=>i.number).join(" · ")||c.code}<br/><small>{c.versions.length} {c.versions.length===1?"versão disponível":"versões disponíveis"} · {c.current_published_id?"com publicação":"sem versão publicada"}</small></span><span aria-hidden="true"> →</span></button>)}
            {sources.data.total>25 && <div className="experience-footer"><span>{sources.data.total} compras</span><button disabled={!sourcesOffset} onClick={()=>go({sources_page:String(sourcesOffset/25-1)})}>Compras anteriores</button><button disabled={sourcesOffset+25>=sources.data.total} onClick={()=>go({sources_page:String(sourcesOffset/25+1)})}>Mais compras</button></div>}</>}
          {selectedCase && <><div className="experience-toolbar"><label>Compra<span>{selectedCase.reference||selectedCase.code}</span></label><label>Versão<select id="cost-version" value={versionId||""} onChange={e=>go({version:e.target.value||null})}><option value="">Escolher versão</option>{selectedCase.versions.map(v=><option key={v.id} value={v.id}>{v.number} · {kindLabel[v.kind]} · {statusLabel[v.status]}{v.id===selectedCase.current_published_id?" · vigente":""}</option>)}</select></label></div>{state(cost)}
            {currentCost && <><div className="experience-cost-hero"><div className="experience-cost-value">{money(currentCost.product?.unit_brl)} <small style={{fontSize:18}}>/ {row.unit||"unidade-base"}</small></div><button className="primary" id="open-cost-composition" onClick={()=>go({section:"sources"})}>Ver composição e origem →</button></div>
              <p className="experience-cost-subtitle">Versão {currentCost.number} · {kindLabel[currentCost.kind]} · {statusLabel[currentCost.status]} · Base de {number(currentCost.product?.qty)} {row.unit||"unidades"}</p>
              <p><span className="experience-tag">{{documental:"Câmbio documental",bancario:"Câmbio bancário realizado",parcial:"Cobertura cambial parcial"}[currentCost.fx.kind||""]||"Natureza cambial a conferir"}</span> <span className="experience-tag">{currentCost.partial_coverage?(currentCost.status==="DRAFT"?"Cobertura parcial":"Publicação parcial"):"Cobertura "+(currentCost.coverage.coverage==="COMPLETE"?"completa":"a conferir")}</span> <span className="experience-tag">Tributos brutos</span></p>
              <p className="muted">Total deste produto na compra: {money(currentCost.product?.total_brl)}. A quantidade-base do custo não é o saldo atual do estoque.</p>
              {selectedCase.purchases.length>0 && <p className="muted">Pedido: {selectedCase.purchases.map(p=>p.code).join(" · ")}</p>}
            </>}{versionId>0 && cost.data && !currentCost && <p role="alert">A versão não pertence à compra selecionada.</p>}</>}
        </>}
      </section>
    </>}
    {(section || docId>0) && <>{state(cost)}{currentCost && !docId && <><p className="muted">{selectedCase?.reference||selectedCase?.code} · versão {currentCost.number} · {kindLabel[currentCost.kind]} · base de {number(currentCost.product?.qty)} {row?.unit||"unidades"} · tributos brutos{currentCost.partial_coverage?" · publicação parcial":""}</p><p><strong>{money(currentCost.product?.total_brl)}</strong> atribuídos a este produto. A coluna da compra mostra o componente inteiro, não o custo do estoque atual.</p>
      <div className="experience-table-wrap"><table className="experience-table"><thead><tr><th>Componente</th><th className="numeric">Neste produto</th><th className="numeric">Na compra</th><th>Origem</th></tr></thead><tbody>{currentCost.components.map(c=><tr key={c.id}><td>{componentLabel[c.type]||c.type.replaceAll("_"," ")}<small>{c.included?"Incluído":"Fora do total"}</small></td><td className="numeric">{money(c.product_brl)}</td><td className="numeric">{money(c.process_brl)}</td><td>{c.documents.length?c.documents.map(d=><button className="text-button" id={`source-document-${d.id}-${c.id}`} key={d.id} onClick={()=>go({doc:String(d.id)})}>{d.name} ↗</button>):<span className="muted">Documento ausente ou sem acesso</span>}</td></tr>)}</tbody></table></div>
      {!currentCost.components.some(c=>c.type.includes("FRETE")||c.type.includes("FREIGHT")) && <p className="muted">Frete não informado nesta composição.</p>}
      <details className="experience-source"><summary>Referência cambial e cobertura</summary><p>{currentCost.fx.kind==="documental"?"Conversão documental; não representa câmbio bancário realizado.":"Consulte a natureza cambial desta versão."} {currentCost.fx.documentary_rate?`Taxa documental: ${number(currentCost.fx.documentary_rate)}.`:"Taxa documental não informada."}</p><p>{currentCost.partial_coverage?"Publicação com cobertura parcial.":"Cobertura informada pela versão: "+(currentCost.coverage.coverage||"não informada")}</p></details>
    </>}{docId>0 && currentCost && (doc ? <div className="experience-document" data-testid="stock-source-document"><PdfViewerPanel key={doc.id} contentUrl={`/api/documents/${doc.id}/content`} activeLocator={null} compactChrome /></div>:<p role="alert">Documento não disponível nesta versão ou para seu acesso.</p>)}</>}
  </section>;
  return <section className="experience-page stock-positions-page" data-testid="stock-positions">
    <div className="experience-heading"><div><h1 ref={heading} tabIndex={-1}>Estoque atual</h1></div><Link className="experience-link" to="/inventory/movements">Ver movimentos</Link></div>
    {list.data && <dl className="experience-stats">{list.data.totals.map(t=>t.unit?Object.entries(regimes).map(([k,label])=><div key={k+t.unit}><dt>{label}</dt><dd>{number(t.quantities[k as keyof typeof regimes])} <small>{t.unit}</small></dd></div>):<div key="unit-missing"><dt>Unidade a conferir no cadastro</dt><dd>{t.sku_count} <small>{t.sku_count===1?"produto · quantidade no detalhe":"produtos · quantidades por produto na lista"}</small></dd></div>)}</dl>}
    <div className="experience-toolbar"><label>Buscar produto<input aria-label="Buscar produto" value={params.get("q")||""} placeholder="Nome ou SKU" onChange={e=>go({q:e.target.value||null,page:null},true)} /></label>
      <label>Posição<select aria-label="Posição" value={params.get("regime")||""} onChange={e=>go({regime:e.target.value||null,page:null})}><option value="">Todas as posições</option>{Object.entries(regimes).map(([k,l])=><option key={k} value={k}>{l}</option>)}</select></label>
      <label>Saldo<select aria-label="Saldo" value={params.get("status")||"positive"} onChange={e=>go({status:e.target.value,page:null})}><option value="positive">Com saldo</option><option value="zero">Sem saldo</option><option value="all">Todos os produtos</option></select></label>
      <label>Ordenar<select aria-label="Ordenar" value={params.get("sort")||"name"} onChange={e=>go({sort:e.target.value,page:null})}><option value="name">Nome A–Z</option><option value="-name">Nome Z–A</option><option value="sku">SKU A–Z</option><option value="-DOMESTIC">Maior disponível</option><option value="DOMESTIC">Menor disponível</option><option value="-BONDED">Maior em entreposto</option></select></label>
      <label>Local<select aria-label="Local" value={params.get("location_id")||""} onChange={e=>go({location_id:e.target.value||null,page:null})}><option value="">Todos os locais</option>{params.get("location_id") && !locations.some(l=>String(l.id)===params.get("location_id")) && <option value={params.get("location_id")!}>Local selecionado · {params.get("location_id")}</option>}{locations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
      {(params.get("q")||params.get("regime")||params.get("status")||params.get("location_id")) && <button onClick={()=>setParams({})}>Limpar filtros</button>}
    </div>{state(list)}
    {list.data && <><p className="muted" style={{fontSize:12}}>{list.data.total} {list.data.total===1?"produto":"produtos"} · totais de todo o recorte · trânsito e liberações não somados ao saldo físico</p>
      {list.data.total===0?<div className="experience-status">Nenhum produto neste recorte. Ajuste a busca ou os filtros.</div>:<div className="experience-table-wrap"><table className="experience-table"><thead><tr><th>Produto</th><th>SKU</th><th className="numeric">Disponível</th><th className="numeric">Entreposto</th><th className="numeric">Quarentena</th><th>Unidade</th></tr></thead><tbody>{list.data.rows.map(p=><tr key={p.product_id}><td><button className="text-button product-name" title={p.name} id={`stock-product-${p.product_id}`} onClick={()=>go({product:String(p.product_id)})}>{p.name}</button></td><td className="stock-sku">{p.sku}</td>{Object.keys(regimes).map(k=><td className="numeric" key={k}>{number(p.quantities[k as keyof typeof regimes])}</td>)}<td>{p.unit||"Não informada"}</td></tr>)}</tbody></table></div>}
      <div className="experience-footer"><span>{list.data.total?`${offset+1}–${Math.min(offset+25,list.data.total)} de ${list.data.total}`:"0 resultados"}</span><button disabled={!offset} onClick={()=>go({page:String(offset/25-1)})}>Anterior</button><button disabled={offset+25>=list.data.total} onClick={()=>go({page:String(offset/25+1)})}>Próxima</button></div>
    </>}
  </section>;
}
