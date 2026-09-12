import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
// Keep browser profiles/cache with the project when the system drive is full.
const temporary=fileURLToPath(new URL('../data/browser-temp/',import.meta.url));
fs.mkdirSync(temporary,{recursive:true});
process.env.TEMP=temporary;
process.env.TMP=temporary;
process.env.TMPDIR=temporary;
