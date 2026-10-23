// Mechanical image packaging; the authored Markdown is the sole advisor artifact.
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const here=dirname(fileURLToPath(import.meta.url)),repo=resolve(here,'../../../..');
const evidence=resolve(repo,'../audit-lab/receiving-20261023/evidence'),report=resolve(here,'../INTEGRACAO_EXPERIENCIA_EPIC.md');
let md=readFileSync(report,'utf8');
md=md.replace(/@@IMAGE:(R\d+):([^@]+)@@/g,(_,id,path)=>{
 const bytes=readFileSync(resolve(evidence,path));if(bytes.subarray(1,4).toString()!=='PNG')throw Error('Not PNG');
 const w=bytes.readUInt32BE(16),h=bytes.readUInt32BE(20),sha=createHash('sha256').update(bytes).digest('hex');
 return `Viewport **${w}×${h}**, escala 100%. PNG ${bytes.length} bytes; SHA256 \`${sha}\`.\n\n![${id}](data:image/png;base64,${bytes.toString('base64')})`;
});
const images=[...md.matchAll(/!\[(R\d+)\]\(data:image\/png;base64,([A-Za-z0-9+/=]+)\)/g)];
if(images.length!==8)throw Error('Expected eight captures');
for(const [,id,b64]of images){const b=Buffer.from(b64,'base64');if(b.toString('base64')!==b64||b.subarray(1,4).toString()!=='PNG')throw Error('Invalid '+id);}
writeFileSync(report,md,'utf8');console.log(JSON.stringify({images:images.length,bytes:Buffer.byteLength(md),sha256:createHash('sha256').update(md).digest('hex')}));
