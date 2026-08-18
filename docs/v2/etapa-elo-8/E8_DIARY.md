# Diário Elo 8

## E8-1 — NAT-REVERSE = B

NAT-REVERSE = B. C local na rota Customs (importar `inventory.public` para guardar reverse) é ciclo: o arch test aplica `ALLOWED_DEPS` a todo o pacote, inclusive `nationalization_routes.py`. A API `POST .../nationalizations/{id}/reverse` permanece capaz de duplicar saldo se chamada fora da UI — item **`E8-NAT-REVERSE-API`** no Roadmap **0.5.121** B.3. E8-2 oculta Reverter quando `received_qty > 0`. Walk não reverteu nacionalização após estoque.

## E8-6 — barras e Blueprint

Walk E8-5 **PASS**. Roadmap **0.5.121**: elo 8 LIGADO (produto no catálogo) + J#5-REC na ressalva; cadeia 8/10; Aduana 2/3. Blueprint **0.2.24**: PATH/BIND/COVERAGE/STUBS. Caso A entreposto = B.6 datado.

Mestre reescrito após o fecho para ficar coerente com Q1–Q7 (sem futuro misturado com DONE). Campanha **não** relançada.

## 0.5.123 — verificação final 202 → estoque

E8-FINAL-VERIFY **PASS** e **ACEITO** pelo advisor (2026-08-17). Campanha **ENCERRADA**. W1–W8 no código final; `e2e:j5` 4/4; família 202 PDFs reais na mesma UI até estoque. B.2 deixa de dizer que o Elo 8 só foi provado com cadeia mock. Barras inalteradas. Backlog intocado: `E8-NAT-REVERSE-API`; J#5-REC; Caso A; `E7-ARRIVAL-GATE`; atritos B.6.

## 0.5.122 — massa do walk e atrito

Hipótese «a 202 real perdeu-se no drop_all do loop de reparo e reconstruí-la era mais caro que o mock»: **parcialmente refutada na causa, confirmada no custo.** O pytest E8-4 (`drop_all`, **antes** do walk) já apagava a massa Elo 7; o loop Q2 apagou de novo. Reconstruir os 5 PDFs seria relançar o Elo 7. Fixture `E8-202-MOCK` / `IMP-C053F7E3E212` foi o caminho autorizado (DEC-E8-DOC). B.2 declara isso; atrito W4/W8 em B.6. Barras inalteradas.
