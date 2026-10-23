import {formatDateTime as fallback} from '../../ui/format';
/** Convert zoned instants to the viewer's timezone; never reinterpret date-only/naive values. */
export function formatDateTime(value:string|null|undefined){
 if(!value||!/(Z|[+-]\d\d:?\d\d)$/.test(value))return fallback(value);
 const date=new Date(value);if(Number.isNaN(date.getTime()))return '—';
 return new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short'}).format(date);
}
