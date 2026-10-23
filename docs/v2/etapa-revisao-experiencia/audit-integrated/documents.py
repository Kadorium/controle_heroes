"""Valid synthetic files for AUD26 UI upload only; no operational data."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
import subprocess
root=Path(__file__).resolve().parents[4].parent/'audit-lab/integrated-20261023/fixtures'
root.mkdir(parents=True,exist_ok=True)
texts={
 'AUD26-invoice.pdf':['AUD26-FAT - Commercial invoice','Supplier: AUD26 Fornecedor sintetico','Order: AUD26-E2E | Date: 23/10/2026','SKU AUD26-RAQ | Raquete Beach Tennis','20 UN x EUR 100.00 = EUR 2,000.00','Total EUR 2,000.00 | Due 23/11/2026'],
 'AUD26-payment.pdf':['AUD26-PAG - Payment evidence','Supplier: AUD26 Fornecedor sintetico','Reference: AUD26-E2E | 23/10/2026','Payment amount: EUR 500.00','Allocation is a separate operation.'],
 'AUD26-declaration.pdf':['AUD26-DI - Synthetic declaration','Order AUD26-E2E | Invoice AUD26-FAT','SKU AUD26-RAQ | Quantity: 20 UN','Goods: EUR 2,000.00 | Documentary rate: BRL 6.00/EUR','Goods equivalent BRL 12,000.00 | Gross II: BRL 300.00','Total example goods plus tax: BRL 12,300.00']}
for name,lines in texts.items():
 p=root/name;c=canvas.Canvas(str(p),pagesize=A4);c.setTitle(name[:-4]);c.setFont('Helvetica-Bold',18);c.drawString(48,790,'EPIC - AUDITORIA FICTICIA')
 c.setFont('Helvetica',12)
 for i,line in enumerate(lines):c.drawString(48,745-i*32,line)
 c.setFont('Helvetica',10);c.drawString(48,470,'Sem validade comercial, fiscal ou bancaria. Laboratorio isolado AUD26.')
 c.save();d=PdfReader(p);assert len(d.pages)==1 and 'AUD26' in d.pages[0].extract_text();subprocess.run(['pdftoppm','-scale-to','1000','-singlefile','-png',str(p),str(p.with_suffix(''))],check=True)
print('3 synthetic PDFs rendered and text checked in '+str(root))
