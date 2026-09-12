import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const folder=new URL('../docs/verification/',import.meta.url);
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:960}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try {
  await page.goto('http://127.0.0.1:8000/dashboard/');
  const nav=label=>page.getByRole('navigation').getByRole('button',{name:label,exact:true}).click();
  await nav('Find vehicle');
  await page.getByLabel('Vehicle registration').fill('ZPN720');
  await page.locator('main').getByRole('button',{name:'Find vehicle',exact:true}).click();
  await page.getByRole('heading',{name:'ZPN720',exact:true}).waitFor();
  const trace=await (await page.request.get('http://127.0.0.1:8000/api/investigation/trace/ZPN720')).json();
  assert.ok(trace.distinct_cameras>=2);
  const garage=trace.route.find(r=>r.camera_id==='PUBLIC-GARAGE');
  assert.ok(garage);assert.equal(garage.source_type,'RECORDED');
  assert.equal(garage.geo_source,'UNKNOWN');
  await page.getByText('Camera locations have not been supplied. Observations and evidence are listed below.',{exact:true}).waitFor();
  await page.screenshot({path:fileURLToPath(new URL('two-scene-vehicle-trace-sept12.png',folder))});
  const telemetry=await (await page.request.get('http://127.0.0.1:8000/api/anpr/stats')).json();
  assert.equal(telemetry.ocr_engine,'PLATE_ONNX_CCT_S_V2');assert.equal(telemetry.ready,true);
  assert.deepEqual(errors,[]);
  await fs.writeFile(new URL('plate-ocr-browser-sept12.json',folder),JSON.stringify({passed:true,engine:telemetry.ocr_engine,distinct_recorded_cameras:trace.distinct_cameras,errors},null,2));
  console.log('PASS: actual plate OCR readiness and two-recording vehicle trace in browser');
} finally {await browser.close();}
