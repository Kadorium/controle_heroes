# Matriz evidências — patch fechamento J#5

| Requisito | Teste | Screenshot / log |
|---|---|---|
| KPIs sem soma cross-currency | `test_ap_queue_kpis_never_mix_currencies` | `j5-10-customs-payable-ap.png` |
| Drawer Customs só Numerário + notice | e2e j5-acceptance §10 | `j5-10-customs-payable-ap.png` |
| GET funding público / Opção B | `test_customs_payable_not_in_eligible_list` + arch | — |
| Boundaries billing/reporting ↛ customs | `test_billing_reporting_do_not_depend_on_customs` | — |
| RECLASS conservação física | `test_sku_position_buckets` + e2e SC-10 | `j5-13-sku-position.png` |
| Ledger RECLASS_OUT/IN + locais legíveis | e2e §14 | `j5-14-inventory-movements.png` |
| Stubs “Não disponível” | e2e sku-bucket-in_clearance | `j5-13-sku-position.png` |
| e2e:j5 completo | 4 specs PASS | `logs/patch-close-e2e-j5.txt` |
