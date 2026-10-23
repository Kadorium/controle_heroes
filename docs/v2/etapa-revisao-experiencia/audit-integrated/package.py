"""Build one reviewed audit ZIP; validate extraction, PNGs, refs and secrets.

No application writes, migrations, seed or browser calls. Run after reviewed push.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import hashlib,json,re,shutil,subprocess,tempfile,zipfile,sys,os
from PIL import Image

repo=Path(__file__).resolve().parents[4];folder=repo/'docs/v2/etapa-revisao-experiencia'
lab=repo.parent/'audit-lab/integrated-20261023';raw=lab/'package'
name='AUDITORIA_E2E_UX_EXECUTIVA_EPIC';source=folder/(name+'.md')
git=lambda *a:subprocess.check_output(['git',*a],cwd=repo).decode('utf8').strip()
branch=git('branch','--show-current');head=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/'+branch)
assert remote.split()[0]==head,'Publish reviewed audit files before final package'
assert not git('diff','--name-only','--','v2/app','v2/frontend/src','v2/alembic'),'Product change not authorized'
text=source.read_text(encoding='utf8');counts=Counter()
for line in text.splitlines():
    if re.match(r'^\| [A-Z]+-\d+ \|',line):counts[line.split('|')[4].strip()]+=1
summary=f"**Cobertura: {sum(counts.values())} cenários inventariados: {counts['A']} aprovados, {counts['F']} falharam, {counts['B']} bloqueados, {counts['N']} não executados e {counts['NA']} não aplicáveis.** Aprovados + falhas = {counts['A']+counts['F']} cenários com resultado funcional no alcance especificado. Não é porcentagem de aceite global do produto; bloqueados incluem conferência física e trecho de custo."
text=text.replace('<!-- COVERAGE -->',summary)
stage=Path(tempfile.mkdtemp(prefix='epic-audit-package-'));(stage/'prints').mkdir();(stage/'evidencias').mkdir()

# Reviewed selection: original PNGs, no base64, no login screens or harness-failure screenshots.
gallery='''
EXE-01_01_1366x681.png|/dashboard|admin|Executiva carregada; esperado contexto financeiro e prioridade, observado exposição EUR qualificada e origem clicável.
CAT-01_01_1366x681.png|/catalog/products|admin|Catálogo carregado; variantes existentes; repetição de incompletude e ausência de mídia (U-03).
COM-01_01_1366x681.png|/orders|admin|Lista de pedidos; consulta, não aprovação de todas as ações.
FAT-01_01_1366x681.png|/invoices|admin|Lista de faturas carregada; estados e saldos.
FIN-01_01_1366x681.png|/payables|admin|Resumo e fila antes da massa auxiliar de paginação.
PAG-01_01_1366x681.png|/payments|admin|Lista de pagamentos; não confundir registro com alocação.
LOG-01_01_1366x681.png|/shipments|admin|Lista de embarques carregada.
LOG-02_01_1366x681.png|/logistics-providers|admin|Prestadores existentes; somente consulta, CRUD não testado.
ADU-01_01_1366x681.png|/customs|admin|Lista de processos e estados operacionais.
REC-01_01_1366x681.png|/inventory/receiving|admin|Entrada de recebimentos, distinta de liberar na Aduana.
EST-01_01_1366x681.png|/inventory/positions|admin|Posição atual com medidas econômicas e cobertura.
MOV-01_01_1366x681.png|/inventory/movements|admin|Movimentos com data, local e regime; leitura não certifica escrita de ajustes.
CUS-01_01_1366x681.png|/costing|admin|Fila de custos; números sem formatação monetária uniforme (U-04).
ING-01_01_1366x681.png|/ingestion|admin|Fila inicialmente vazia; sem fingir extração concluída.
ADM-01_01_1366x681.png|/admin/users|admin|Quatro perfis iniciais; consulta de usuários.
FOR-01_01_1366x681.png|/catalog/suppliers|admin|Lista de fornecedores antes da edição AUD26.
PRE-01_01_1366x681.png|/catalog/prices/import|admin|Importação de preços, entrada secundária pelo catálogo.
EST-02_01_multisselecao.png|/inventory/positions|admin|Esperado Roupas OU Raquetes OU Bolas E Beach Tennis; observado três tipos selecionados.
EST-02_02_capital.png|/inventory/positions|admin|Custo decrescente; SHOW26 concentra maior capital no recorte; totais invariantes.
EST-02_07_produto_carregado.png|/inventory/positions?product_id=3|admin|Produto contextual carregado e compras distintas; não usar somente última compra.
EST-02_04_composicao.png|/inventory/positions?product_id=3&section=cost|admin|Composição da compra escolhida e qualificadores de versão/base.
EST-02_05_documento.png|/inventory/positions (documento contextual)|admin|PDF real renderizado, origem do custo; depois retorno com defeito de foco F-06.
EST-03_01_pagina2.png|/inventory/positions?offset=25|admin|Segunda página; totais globais iguais; contexto restaurado por Back com tabela explícita.
EST-03_02_erro.png|/inventory/positions|admin|503 simulado exclusivamente neste caso; mensagem e tentar novamente, não zero.
EST-03_03_recuperado.png|/inventory/positions?q=SHOW26|admin|Consulta real recuperada; 42 UN / 54.900 / 138.138.
EST-03_04_vazio.png|/inventory/positions?q=AUD26-NADA|admin|Consulta válida sem resultado, distinta do erro.
EST-04_01_multimodal.png|/inventory/positions?modality_ids=bt,padel|admin|Multimodalidade selecionada pela UI; sem IDs de SKU duplicados no apoio técnico.
COM-02_01_formulario.png|/orders/new|comprador|Formulário AUD26: 20 UN × EUR100; antes de confirmar.
COM-02_02_confirmacao.png|/orders/new|comprador|Confirmação explícita da compra; esperado EUR2.000.
COM-02_03_persistido.png|/orders/14|comprador|Compra persistida após recarga.
FAT-02_02_conferencia.png|/invoices/14|comprador|Conferência de emissão e termos antes da gravação.
FAT-02_03_emitida_recarregada.png|/invoices/14|comprador|Fatura emitida e obrigação após recarga; PDF anexado correspondente.
FIN-02_03_confirmar_alocacao.png|/payments/10|comprador|Conferência EUR500 antes de liquidar; registro sem alocar não reduziu obrigação.
FIN-02_04_alocacao_persistida.png|/payments/10|comprador|Alocação persistida; obrigação fica EUR1.500.
FIN-03_01_detalhe_vencida.png|/payables (drawer)|admin|Obrigação A EUR2.000 vencida; Escape fecha e preserva filtro.
LOG-04_01_excesso.png|/shipments/11|admin|Tentativa 21 quando pedido permite20; bloqueio real.
LOG-04_04_chegada_reaberta.png|/shipments/11|admin|Chegada persistida, reaberta na conferência final; não implica nacionalização automática.
ADU-02_02_vinculos_reabertos.png|/customs/11|aduana|Vínculos por IDs reabertos na conferência final; auxílio técnico necessário (U-02).
ADU-03_01_excesso.png|/customs/11|aduana|Liberação acima do saldo rejeitada.
ADU-03_02_liberado.png|/customs/11|aduana|20 liberadas; não significa recebimento realizado.
REC-02_02_conferencia_parcial.png|/inventory/receiving?item=43|estoque|Conferência parcial8UN; nome temporário decorrente do defeito de cancelar, corrigido depois.
REC-02_04_resposta_perdida.png|/inventory/receiving?item=43|estoque|Falha de resposta simulada após gravação real dos12 restantes; repetir usa mesma operação.
REC-02_05_completo.png|/inventory/receiving?item=43|estoque|20 recebidas / zero pendente; nome temporário anterior à restauração do cadastro.
REC-02_07_saldo_reaberto.png|/inventory/sku/43|estoque|Saldo físico após recebimentos8+12, reaberto com cadastro original restaurado.
REC-03_01_concorrencia.png|/inventory/receiving (QA-RCV-RACE)|estoque|Sessão perdedora da disputa por2; outra confirmação venceu; estoque não duplicou.
REC-03_02_nao_liberado.png|/inventory/receiving (QA-RCV-BLOCKED)|estoque|Origem não liberada: sem ação de confirmar recebimento.
CUS-02_02_publicado.png|/costing/9|admin|F-01/F-02: custo0 publicado, cobertura completa e natureza cambial incorreta.
CUS-03_01_vinculo_exclusivo.png|/customs/12|admin|409 correto ao tentar reutilizar fatura; controle positivo não executado.
CAT-03_01_cancelamento_rascunho_retido.png|/catalog/products/43/edit|comprador|F-05: rascunho cancelado reaparece; defeito reproduzido.
CAT-04_01_comparacao.png|/catalog/products/compare?ids=3,5|admin|Comparar diferenças SHOW26/ARION26; texto técnico desnecessário.
PRE-02_01_intervalo_invalido.png|/catalog/products/43|admin|Preço: intervalo inválido não gravado.
PRE-02_02_sobreposicao.png|/catalog/products/43|admin|Sobreposição de vigência bloqueada.
PRE-02_03_historico.png|/catalog/products/43|admin|Histórico1.000→1.100 e futuro1.200; vigência atual/futura identificável.
PRE-02_04_reflexo_estoque.png|/inventory/positions?q=AUD26-RAQ|admin|Venda22.000; custo/margem ausentes, não zero.
PRE-03_01_erros.png|/catalog/prices/import|admin|CSV unidade/SKU inválidos; erros por linha; confirmação bloqueada.
PRE-03_02_previa.png|/catalog/prices/import|admin|Prévia válida:1criar na tabela auxiliar; confirmação explícita.
PRE-03_03_confirmado.png|/catalog/prices/import|admin|Confirmação repetida após resposta perdida; um único registro.
ING-02_01_invalido.png|/ingestion|comprador|TXT rejeitado com status Pronto/Rejeitado ambíguo (U-05).
ING-03_01_workspace.png|/ingestion/1|admin|PDF genérico renderizado sem extração válida; commit bloqueado, não parser de fornecedor aprovado.
EXE-02_01_personalizar.png|/dashboard (visão pessoal)|admin|Cópia pessoal reordenada/ocultada; persistiu na recarga.
FOR-02_01_fornecedor.png|/catalog/suppliers/5|comprador|País/código editados; inativação/reativação persistidas.
ADM-02_01_usuario_inativo.png|/admin/users (detalhe AUD26)|admin|Usuário estoque inativo; login posterior negado; campos de senha vazios.
FIN-05_01_fila_sem_paginacao.png|/payables|admin|F-03:50 de59 abertas sem controle de próxima página.
FIN-06_01_resumo_pagina1.png|/payables?offset=0|admin|F-04:Por alocar2650 na primeira página.
FIN-06_02_resumo_pagina2.png|/payables?offset=50|admin|F-04:Por alocar2550, mesmos saldos e filtros.
V-DASH_1366x681.png|/dashboard|admin|Primeira dobra no laptop, após AUD26: indicadores e prioridade; estoque abaixo.
V-STOCK_1366x768.png|/inventory/positions|admin|Laptop681→768 aumenta linhas úteis; sem reduzir fonte.
V-STOCK_1024x768.png|/inventory/positions|admin|Janela estreita:4linhas inteiras, textos longos e scroll interno de tabela.
V-DASH_1920x1080.png|/dashboard|admin|FullHD, mesma direção/layout real.
V-AP_1366x681.png|/payables|admin|5obrigações inteiras na primeira dobra, resumos compactos.
V-PRICE_1366x681.png|/catalog/products/43|admin|U-01:preços não aparecem na primeira dobra; primeira linha em y1402.
V-RECEIVE_1024x768.png|/inventory/receiving|admin|Fila estreita preserva origem/quantidade; avaliação de viewport, não laptop físico.
tour-target-unavailable.png|tour alvo indisponível|admin|Falha simulada de alvo; passo interrompe e explica; não inventa dado.
'''
entries=[]
for row in gallery.strip().splitlines():
    filename,route,profile,caption=row.split('|');entries.append((filename,route,profile,caption))
tour_routes=['/dashboard','/orders/2/commercial','/invoices/2','/payments/2','/shipments/2','/customs/2','/inventory/positions','/costing/2']
for i,route in enumerate(tour_routes,1):entries.append((f'tour-50s-{i}.png',route,'admin',f'TOUR-01 etapa{i}/8, ritmo50s, alvo carregado; sem gravação de negócio.'))
parts=[];image_index=[]
for file,route,role,caption in entries:
    src=raw/'prints'/file;assert src.is_file(),file
    with Image.open(src) as img:img.load();assert img.format=='PNG';w,h=img.size
    shutil.copy2(src,stage/'prints'/file)
    ident=file.removesuffix('.png');image_index.append({'file':'prints/'+file,'case':ident,'profile':role,'route':route,'viewport':[w,h],'scale':1,'build':'receiving-stock-20261023.1','caption':caption,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
    parts.append(f'### {ident}\n\n{role} · `{route}` · {w}×{h}, 100% · {caption}\n')
    if f'](prints/{file})' not in text:parts.append(f'![{ident}](prints/{file})\n')
    else:parts.append(f'[Imagem já apresentada no achado](prints/{file}).\n')
text=text.replace('<!-- GALLERY -->','\n'.join(parts))

evidence=['ACL-02','ADU-02','ADU-03','ADM-02','CAT-03','CAT-04','COM-02','COM-03','CUS-02','CUS-02-preview','CUS-03','DOC-01','EST-02','EST-02-return','EST-03','EST-04','EXE-02','EXE-03','FAT-02','FIN-02','FIN-03','FIN-05','FIN-06','FINAL-READ','FOR-02','ING-02','ING-03','INV-01','LOG-04','PRE-02','PRE-03','REC-02-before','REC-02-partial','REC-02','REC-03','VIS-01','reconciliation']
def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if not re.search(r'token|password|cookie|authorization|secret|request_key|session',k,re.I)}
    if isinstance(x,list):return [clean(v) for v in x]
    return x
for item in evidence:
    p=raw/'evidencias'/(item+'.json');data=clean(json.loads(p.read_text(encoding='utf8')))
    if item=='CUS-02-preview':data['expected_qualification']='Conditional hypothetical complete allocation only. Original process has no invoice-line allocation: expected incomplete, NOT assertion of12300 as payable cost.'
    (stage/'evidencias'/p.name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
shutil.copy2(raw/'prints/tour-50s-itinerary.json',stage/'evidencias/tour-50s-itinerary.json')
(stage/'evidencias/image-index.json').write_text(json.dumps(image_index,ensure_ascii=False,indent=2),encoding='utf8')
now=datetime.now(ZoneInfo('America/Sao_Paulo'));sha=hashlib.sha256
gitproof={'at_brasilia':now.isoformat(),'branch':branch,'initial_head':'b50c8d6d51d95272b60dc01b0660eac4e260bf43','audit_commit':head,'remote_url':'https://github.com/Kadorium/controle_heroes.git','ls_remote':remote,'equal':remote.split()[0]==head,'served_source':'e48f7c283ea201e56d658f6ddb2dcb9f1ab96157','delivery_tag_target':git('rev-list','-n','1','delivery/receiving-stock-20261023.1'),'reviewed_commit_files':git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()}
(stage/'evidencias/git-verified.json').write_text(json.dumps(gitproof,ensure_ascii=False,indent=2),encoding='utf8')
closing=f'''## 11. Fechamento publicado e verificação do pacote

Consulta remota em {now.strftime('%d/%m/%Y %H:%M:%S')} Brasília. Branch `{branch}`; commit de auditoria/documentação **`{head}`**. Referência remota consultada: `{remote}`. **Local = remoto.**

[Commit revisado no GitHub](https://github.com/Kadorium/controle_heroes/commit/{head}). O código servido continua **e48f7c283ea201e56d658f6ddb2dcb9f1ab96157**; nenhum novo bundle foi publicado. A tag da entrega de produto aponta para esse mesmo e48. O commit de auditoria não deve ser anunciado como revisão de código servido.

Conteúdo público limitado aos arquivos revisados da rodada. PNGs, leituras brutas, backups e este ZIP não foram publicados. Detalhe auditável em `evidencias/git-verified.json`. O MD do ZIP acrescenta os hashes obtidos após o push; o texto-base e o empacotador foram versionados no próprio commit (evita hash autorreferencial).

Validação do pacote: extração em diretório temporário novo; CRC de todas as entradas; abertura UTF-8 do MD e JSONs; decodificação integral de todos os {len(entries)} PNGs; existência de todas as referências relativas; correspondência de nomes/legendas; varredura de segredos e exclusão por allowlist. Resultado técnico no arquivo `evidencias/package-validation.json`. Não há credenciais, cookies, dumps, traces, ZIPs aninhados ou anexos fora da revisão.
'''
text=text.replace('<!-- GIT_CLOSURE -->',closing)
(stage/(name+'.md')).write_text(text,encoding='utf8')
refs=re.findall(r'\]\((prints/[^)]+\.png)\)',text)
assert all((stage/r).is_file() for r in refs)
assert set(refs)=={'prints/'+e[0] for e in entries}
for p in stage.rglob('*'):
    if p.is_file() and p.suffix in ['.md','.json']:
        content=p.read_text(encoding='utf8')
        assert not re.search(r'(?i)bearer\s+[a-z0-9._-]+|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY|"(?:password|cookie|authorization|access_token)"\s*:',content),p
        assert not any(secret and secret in content for secret in [os.getenv('AUDIT_ADMIN_PASSWORD'),os.getenv('AUDIT_ROLE_PASSWORD')]),p
validation={'coverage':dict(counts),'scenarios':sum(counts.values()),'png_count':len(entries),'references':len(refs),'missing_refs':[],'secrets_scan':'passed allowlist + denied keys + known login secret strings','stage': 'isolated temporary directory','format':'Original PNG; no base64','zip_test':'CRC/extract/decode required before success'}
(stage/'evidencias/package-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf8')
if '--check' in sys.argv:
    print(json.dumps({'check_only':True,'stage':str(stage),**validation},ensure_ascii=False));raise SystemExit(0)
target=folder/f'{name}_{now:%Y%m%d-%H%M}.zip';assert not target.exists(),'Do not overwrite an existing audit package'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(stage.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(stage).as_posix())
extract=Path(tempfile.mkdtemp(prefix='epic-audit-verify-'))
with zipfile.ZipFile(target) as z:assert z.testzip() is None;z.extractall(extract)
assert (extract/(name+'.md')).read_text(encoding='utf8')==text
for p in (extract/'prints').glob('*.png'):
    with Image.open(p) as img:img.load();assert img.format=='PNG'
for p in (extract/'evidencias').glob('*.json'):json.loads(p.read_text(encoding='utf8'))
assert all((extract/r).is_file() for r in refs)
validation['zip_test']='PASS: CRC, extracted MD equality, JSON parsing, every PNG fully decoded, every image reference exists'
(stage/'evidencias/package-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf8')
# Repack only this newly generated archive to include the completed verifier result.
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(stage.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(stage).as_posix())
final_extract=Path(tempfile.mkdtemp(prefix='epic-audit-final-verify-'))
with zipfile.ZipFile(target) as z:assert z.testzip() is None;z.extractall(final_extract)
assert (final_extract/(name+'.md')).read_text(encoding='utf8')==text
assert all((final_extract/r).is_file() for r in refs)
for p in (final_extract/'prints').glob('*.png'):
    with Image.open(p) as img:img.load()
for p in (final_extract/'evidencias').glob('*.json'):json.loads(p.read_text(encoding='utf8'))
result={'zip':str(target),'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()).hexdigest(),'images':len(entries),'scenarios':sum(counts.values()),'counts':dict(counts),'extracted':str(extract),'verified':True,'audit_commit':head}
(lab/'package-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
