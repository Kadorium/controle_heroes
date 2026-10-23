import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {ApCompactSummary} from './ApCompactSummary';
afterEach(cleanup);
it('keeps zero, absent amounts and currencies distinct',()=>{
 render(<ApCompactSummary currencies={[{currency:'BRL',open_balance:'0',overdue_balance:null},{currency:'EUR',open_balance:'123456789.90'}]} credits={[]} onOpen={()=>{}} onDue={()=>{}} onCredit={()=>{}}/>);
 expect(screen.getByLabelText('Saldo aberto BRL')).toHaveTextContent('BRL 0,00');expect(screen.getByLabelText('Vencido BRL')).toHaveTextContent('—');expect(screen.getByLabelText('Saldo aberto EUR')).toHaveTextContent('EUR 123.456.789,90');
});
it('preserves drill filters and labels full payment queue',()=>{
 const open=vi.fn(),due=vi.fn(),credit=vi.fn();render(<ApCompactSummary currencies={[{currency:'EUR',open_balance:'1200'}]} credits={[{currency:'EUR',unallocated_candidates_total:'500'}]} onOpen={open} onDue={due} onCredit={credit}/>);
 fireEvent.click(screen.getByLabelText('Saldo aberto EUR'));expect(open).toHaveBeenCalledWith('EUR');fireEvent.click(screen.getByLabelText('Vencido EUR'));expect(due).toHaveBeenCalledWith('overdue','EUR');fireEvent.click(screen.getByLabelText(/Pagamentos por alocar EUR/));expect(credit).toHaveBeenCalled();expect(screen.getAllByText(/fila completa/).length).toBeGreaterThan(0);
});
