"""Additional prerequisites; subsequent receipt/expense/allocation via UI only."""
import json
import seed as s
story=s.purchase('UI-PART',[(s.products[3],6,180)],30,freight=200,tax=300,other=100,receive=[],stages=3)
s.pdf('ui-expense','Despesa adicional de demonstração',[['Descrição','Valor BRL'],['Armazenagem fictícia','120.00']],'Despesa preparada para inclusão e revisão do custo pela interface.')
(s.OUT/'ui-partial.json').write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf8')
print('Prepared partial receipt:',story['process']['id'])
