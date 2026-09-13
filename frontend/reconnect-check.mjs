import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage();let connected=true;const errors=[];
page.on('pageerror',error=>errors.push(error.message));
try {
  await page.route('**/api/cameras',route=>route.fulfill({json:[{id:'UI-IMAGE-TEST',name:'Isolated image-load fixture',source_type:'RECORDED',connection_status:connected?'CONNECTED':'DISCONNECTED',stream_telemetry:{worker_running:connected}}]}));
  await page.route('**/api/cameras/UI-IMAGE-TEST/annotated',route=>route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1cAAAAASUVORK5CYII=','base64')}));
  await page.route('**/api/cameras/UI-IMAGE-TEST/disconnect',route=>{connected=false;return route.fulfill({json:{status:'SUCCESS'}});});
  await page.route('**/api/cameras/UI-IMAGE-TEST/connect',route=>{connected=true;return route.fulfill({json:{status:'SUCCESS'}});});
  await page.goto('http://127.0.0.1:8000/dashboard/#cameras');
  await page.waitForFunction(()=>document.querySelector('img[alt="CCTV Stream UI-IMAGE-TEST"]')?.naturalWidth===1);
  assert.equal(await page.getByRole('button',{name:'Reconnect Camera',exact:true}).isVisible(),false);
  await page.getByTitle('Disconnect Stream',{exact:true}).click();
  const reconnect=page.getByRole('button',{name:'Reconnect Camera',exact:true});
  await reconnect.waitFor({state:'visible'});
  await reconnect.click();
  await page.getByTitle('Disconnect Stream',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('img[alt="CCTV Stream UI-IMAGE-TEST"]')?.naturalWidth===1);
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASS: successful image load, disconnect, visible reconnect, and reconnect. No real camera was changed.');
} finally {await browser.close();}
