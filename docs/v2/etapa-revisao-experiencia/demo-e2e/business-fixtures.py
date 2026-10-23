"""Prepare prerequisites only. Subsequent transitions are exercised by Playwright UI."""
import json
import seed as s
story=s.purchase('UI-LOG',[(s.products[2],6,180)],30,freight=200,tax=300,other=100,receive=[],stages=3)
s.pdf('ui-invoice','Fatura de teste funcional UI',[['Produto','Quantidade','Preço EUR','Total EUR'],['Produto QA de demonstração','13 UN','100','1300'],['TOTAL','','','1300']],'Documento para compra criada e fatura emitida pela UI. Condição: EUR 600 + EUR 700.')
s.pdf('ui-payment','Comprovante fictício UI',[['Pagamento interno','Valor EUR'],['Teste funcional UI','1000']],'Pagamento fictício. Não representa operação bancária externa.')
(s.OUT/'ui-fixture.json').write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf8')
print('UI process prerequisite prepared:',story['process']['id'])
