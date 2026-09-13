import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const folder=process.env.SENTINEL_CAPTURE_DIR ? pathToFileURL(process.env.SENTINEL_CAPTURE_DIR.replace(/[\\/]$/, '') + '/') : new URL('../docs/verification/',import.meta.url);
await fs.mkdir(folder,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:960},recordVideo:{dir:fileURLToPath(folder),size:{width:1440,height:960}}});
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
const base='http://127.0.0.1:8000';const camera='PUBLIC-CARPARK';
const report={started_at:new Date().toISOString(),source:'UVG-VCM Car Park, Tampere University, CC BY 4.0',source_url:'https://tie-ultravideo.rd.tuni.fi/UVG-VCM/index.html',scope:'Real public Finnish video through our operational backend. Representative watchlist only. Not Indian accuracy or a multi-camera journey.'};
const nav=label=>page.getByRole('navigation').getByRole('button',{name:label,exact:true}).click();
try {
 await page.goto(base+'/dashboard/');
 const before=await (await page.request.get(base+'/api/alerts')).json();const old=new Set(before.map(a=>a.id));report.baseline_alert_ids=[...old];
 await nav('Camera registry');await page.getByRole('button',{name:'Add camera',exact:true}).click();
 const form=page.getByRole('dialog',{name:'Camera onboarding'});
 for(const [label,value] of [['Camera ID',camera],['Camera name','Public sample - UVG Car Park (Finland)'],['Location','UVG-VCM public dataset; coordinates not supplied'],['Source system / vendor','UVG-VCM / Tampere University / CC BY 4.0'],['Source URL or recording filename','public-uvg/CarPark.mp4'],['Owner','Tampere University public dataset']]) await form.getByLabel(label,{exact:true}).fill(value);
 await form.getByLabel('Source type').selectOption('RECORDED');await form.getByLabel('Camera type').selectOption('FILE');
 await page.waitForTimeout(7000);await form.getByRole('button',{name:'Save camera',exact:true}).click();await form.waitFor({state:'hidden'});
 await nav('Watchlist');await page.getByRole('button',{name:'Add vehicle',exact:true}).click();const watch=page.getByRole('dialog',{name:'Watchlist entry'});
 await watch.getByLabel('Registration',{exact:true}).fill('ZPN720');await watch.getByLabel('Severity').selectOption('LOW');await watch.getByLabel('Description',{exact:true}).fill('Demonstration only; not a suspect or stolen vehicle. Original licensed UVG-VCM Car Park footage from Finland.');await watch.getByLabel('Record source',{exact:true}).fill('PUBLIC_SAMPLE_TEST');await page.waitForTimeout(7000);await watch.getByRole('button',{name:'Save entry',exact:true}).click();await watch.waitFor({state:'hidden'});
 await nav('Live Cameras');await page.getByLabel('Search live cameras').fill(camera);await page.getByRole('button',{name:'Reconnect Camera',exact:true}).click();
 await page.waitForFunction(id=>document.querySelector(`img[alt="CCTV Stream ${id}"]`)?.naturalWidth>1280,camera,{timeout:30000});
 await page.getByRole('button',{name:'View Details',exact:true}).click();
 for(let i=0;i<15;i++) {
  await page.waitForTimeout(4000);const alerts=await (await page.request.get(base+'/api/alerts')).json();
  report.new_alerts=alerts.filter(a=>!old.has(a.id)&&a.camera_id===camera&&a.plate_number==='ZPN720');
  console.log(`Public video check ${i+1}: ${report.new_alerts.length} new automatic matches`);
  if(report.new_alerts.length) break;
 }
 assert.ok(report.new_alerts?.length,'A new automatic match must occur during this recording');
 await page.screenshot({path:fileURLToPath(new URL('public-source-recognition.png',folder))});await page.waitForTimeout(5000);
 await page.getByRole('button',{name:'Close camera view',exact:true}).click();await nav('Alerts');await page.getByRole('heading',{name:'Latest matches',exact:true}).waitFor();await page.waitForTimeout(5000);
 await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();
 await page.waitForFunction(()=>document.querySelector('img[alt="Saved registration plate crop"]')?.naturalWidth>0,null,{timeout:10000});
 await page.screenshot({path:fileURLToPath(new URL('public-source-alert-evidence.png',folder))});await page.waitForTimeout(8000);await page.getByRole('button',{name:'Close evidence',exact:true}).click();
 await page.getByRole('button',{name:'Acknowledge',exact:true}).first().click();await page.getByText('Alert acknowledged.',{exact:true}).waitFor();
 await nav('Find vehicle');await page.getByLabel('Vehicle registration').fill('ZPN720');await page.locator('main').getByRole('button',{name:'Find vehicle',exact:true}).click();await page.getByRole('heading',{name:'ZPN720',exact:true}).waitFor();await page.waitForTimeout(6000);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export history',exact:true}).click();await (await download).saveAs(fileURLToPath(new URL('public-source-history.csv',folder)));await page.screenshot({path:fileURLToPath(new URL('public-source-history.png',folder))});
 report.trace=await (await page.request.get(base+'/api/investigation/trace/ZPN720')).json();report.health=await (await page.request.get(base+'/api/system/health')).json();report.finished_at=new Date().toISOString();report.javascript_errors=errors;assert.equal(errors.length,0);
 await fs.writeFile(new URL('public-source-demonstration.json',folder),JSON.stringify(report,null,2));await page.waitForTimeout(5000);
} finally {await context.close();await page.video().saveAs(fileURLToPath(new URL('public-source-demonstration.webm',folder)));await browser.close();}
console.log('PASS: real public-source onboarding, recognition, new automatic watchlist alert, evidence, acknowledgement and history export.');
