import { readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const fichiers=readdirSync(new URL('./',import.meta.url)).filter(n=>n.endsWith('.test.mjs')).map(n=>fileURLToPath(new URL(n,import.meta.url)));
const r=spawnSync(process.execPath,['--test',...fichiers],{cwd:new URL('../web/',import.meta.url),env:process.env,stdio:'inherit'});
process.exit(r.status??1);
