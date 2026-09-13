import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:960}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
let stopped=false,disconnects=0,blocked=0;
try {
  // Simulate only source state/failures; never start or stop an actual camera.
  await page.route('**/api/cameras',route=>route.fulfill({json:[
    {id:'cam06',name:'Test stalled source',connection_status:stopped?'DISCONNECTED':'ERROR',source_type:'GOVERNMENT_REPLAY',stream_telemetry:{worker_running:!stopped,error_message:'Source unavailable'}},
    {id:'cam12',name:'Test additional source',connection_status:'DISCONNECTED',source_type:'GOVERNMENT_REPLAY',stream_telemetry:{worker_running:false}}
  ]}));
  await page.route('**/api/cameras/cam06/disconnect',route=>{stopped=true;disconnects++;return route.fulfill({json:{status:'SUCCESS'}});});
  const detail='Camera limit reached (2). Disconnect another camera before connecting this one.';
  await page.route('**/api/cameras/cam12/connect',route=>{blocked++;return route.fulfill({status:409,json:{detail}});});
  await page.goto('http://127.0.0.1:8000/dashboard/#cameras');
  await page.getByLabel('Search live cameras').fill('cam06');
  await page.getByTitle('Disconnect Stream',{exact:true}).click();
  await page.getByTitle('Connect Stream',{exact:true}).waitFor();
  assert.equal(disconnects,1);
  await page.getByLabel('Search live cameras').fill('cam12');
  await page.getByTitle('Connect Stream',{exact:true}).click();
  await page.getByRole('alert').filter({hasText:detail}).waitFor();
  assert.equal(blocked,1);
  await page.getByRole('button',{name:'System details',exact:true}).click();
  await page.getByRole('row').filter({hasText:'Camera workers'}).waitFor();
  assert.deepEqual(errors,[]);
  await fs.writeFile(new URL('../docs/verification/capacity-browser-sept13.json',import.meta.url),JSON.stringify({passed:true,disconnects,blocked,errors,scope:'UI source/error states simulated; real two-source admission and recovery are verified separately.'},null,2));
  console.log('PASS: stalled-source disconnect, readable admission error and worker status');
} finally {await browser.close();}
