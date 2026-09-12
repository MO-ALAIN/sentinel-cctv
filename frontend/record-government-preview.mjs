import './browser-environment.mjs';
// Capture the actual local interface, never download the organizer's source file.
import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const cameraId=process.argv[2] || 'cam06';
if(!/^[A-Za-z0-9_-]{1,64}$/.test(cameraId)) throw new Error('Invalid camera ID');
const folder=new URL('../docs/verification/',import.meta.url);
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:960},recordVideo:{dir:fileURLToPath(folder),size:{width:1440,height:960}}});
const page=await context.newPage();
const errors=[]; page.on('pageerror',e=>errors.push(e.message));
const checkedAt=new Date().toISOString();
try {
  await page.goto('http://127.0.0.1:8000/dashboard/');
  await page.getByRole('navigation').getByRole('button',{name:'Camera registry',exact:true}).click();
  await page.getByRole('heading',{name:'Camera registry & GIS',exact:true}).waitFor();
  await page.waitForTimeout(7000);
  await page.getByRole('button',{name:'Live Cameras',exact:true}).click();
  await page.getByPlaceholder('Search camera ID or location...').fill(cameraId);
  await page.waitForFunction(id=>document.querySelector(`img[alt="CCTV Stream ${id}"]`)?.naturalWidth===1920,cameraId,{timeout:45000});
  await page.getByAltText(`CCTV Stream ${cameraId}`).click();
  for(let i=0;i<3;i++) {
    await page.waitForTimeout(10000);
    console.log(`Recording actual government feed: ${(i+1)*10}s`);
  }
  await page.screenshot({path:fileURLToPath(new URL(`government-${cameraId}-preview.png`,folder))});
  await page.getByRole('button',{name:'Close camera view',exact:true}).click();
  const downloaded=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export recent detections',exact:true}).click();
  await (await downloaded).saveAs(fileURLToPath(new URL('government-ui-detections-sept11.csv',folder)));
  await page.getByRole('button',{name:'More tools',exact:true}).click();
  await page.getByRole('button',{name:'System status',exact:true}).click();
  await page.waitForTimeout(10000);
  await page.getByRole('navigation').getByRole('button',{name:'Find vehicle',exact:true}).click();
  await page.waitForTimeout(7000);
  await page.getByRole('button',{name:'Camera registry',exact:true}).click();
  await page.getByRole('button',{name:'Coverage',exact:true}).click();
  await page.getByRole('button',{name:'Measure coverage',exact:true}).click();
  await page.getByText('No verified survey boundary supplied. Geographic coverage cannot yet be measured.',{exact:true}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(8000);
  const report={checked_at:checkedAt,finished_at:new Date().toISOString(),scope:'Government-feed UI draft with actual detection export and runtime. Bounded recent observations; not independently labelled accuracy or a proven designated journey.',javascript_errors:errors};
  for(const [key,path] of Object.entries({health:'/api/system/health',camera:`/api/cameras/${cameraId}/health`,registry:'/api/registry/stats',coverage:'/api/registry/coverage/gaps',recognition:`/api/anpr?camera_id=${cameraId}`,detections:`/api/detections?camera_id=${cameraId}&limit=500`})) {
    const response=await page.request.get('http://127.0.0.1:8000'+path);
    if(!response.ok()) throw new Error(`Report request failed: ${key}`);
    report[key]=await response.json();
  }
  await fs.writeFile(new URL('government-preview-output.json',folder),JSON.stringify(report,null,2));
  if(errors.length) throw new Error(errors.join('\n'));
} finally {
  await context.close();
  await page.video().saveAs(fileURLToPath(new URL('government-preview-draft.webm',folder)));
  await browser.close();
}
console.log('Draft interface recording and timestamped runtime report saved.');
