import {it,expect} from 'vitest';
import {formatDateTime} from './localDateTime';
it('formats an instant in the viewer timezone, not a sliced UTC string',()=>{const value='2026-10-23T18:00:00Z';expect(formatDateTime(value)).toBe(new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short'}).format(new Date(value)));});
