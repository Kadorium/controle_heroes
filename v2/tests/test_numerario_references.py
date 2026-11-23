from app.ingestion.adapters.solicitacao_numerario_v1 import _extract_header, _extract_expense_lines


def test_preserves_complete_invoice_references_and_leading_zeros():
    header = _extract_header('S/REFERÊNCIA INV. FAT-EPIC-2026-01/FAT-EPIC-2026-010/0019 EMBARQUE MARITIMA ENTRADA\nN/REFERÊNCIA OP-1 INVOICE FAT-EPIC-2026-01')
    assert header['invoice_refs'] == ['FAT-EPIC-2026-01', 'FAT-EPIC-2026-010', '0019']
    assert header['invoice_ref_first'] == 'FAT-EPIC-2026-01'


def test_numeric_corpus_remains_compatible_and_malformed_text_is_not_a_reference():
    assert _extract_header('S/REFERENCIA INV. 181/202/203 EMBARQUE MARITIMA')['invoice_refs'] == ['181', '202', '203']
    assert _extract_header('S/REFERENCIA INV. FAT-A-01/FAT-B-01')['invoice_refs'] == ['FAT-A-01', 'FAT-B-01']
    assert 'invoice_refs' not in _extract_header('S/REFERENCIA INV. FAT 01 DOCUMENTO ILEGIVEL')


def test_existing_tax_codes_are_not_silently_classified_as_expenses():
    lines = _extract_expense_lines('DESPESAS A SEREM DEBITADAS DE NOSSA CONTA:\nII R$ 1.200,00\nIPI R$ 100,00\nPIS R$ 20,00\nII ADICIONAL DESCONHECIDO R$ 15,00\nFRETE INTERNACIONAL R$ 600,00\nTOTAL DESPESAS DO PROCESSO R$ 1.935,00')
    assert [(line.code, line.category) for line in lines[:3]] == [('II','tax'),('IPI','tax'),('PIS','tax')]
    assert [line.category for line in lines[3:]] == ['expense','expense']
