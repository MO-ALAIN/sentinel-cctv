import './browser-environment.mjs';
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const failures=[];
page.on('pageerror',e=>failures.push(e.message));
const folder=new URL('../docs/verification/',import.meta.url);
await fs.mkdir(folder,{recursive:true});
try {
  const response=await page.goto('http://127.0.0.1:8000/dashboard/');
  assert.equal(response.status(),200);
  await page.getByRole('heading',{name:'What would you like to do?',exact:true}).waitFor();
  await page.screenshot({path:fileURLToPath(new URL('organized-overview.png',folder)),fullPage:true});
  await page.getByRole('navigation').getByRole('button',{name:'Camera registry',exact:true}).click();
  await page.getByRole('heading',{name:'Camera registry & GIS',exact:true}).waitFor();
  const registry=await (await page.request.get('http://127.0.0.1:8000/api/registry/cameras')).json();
  assert.equal(registry.filter(c=>c.source_type==='GOVERNMENT_REPLAY').length,30);
  assert.equal(await page.locator('.police-table-wrap tbody tr').count(),10);
  await page.getByText(new RegExp(`1.10 of ${registry.length} cameras`)).waitFor();
  await page.screenshot({path:fileURLToPath(new URL('current-registry.png',folder)),fullPage:true});
  await page.getByRole('button',{name:'Live Cameras',exact:true}).click();
  await page.getByLabel('Search live cameras').fill('cam06');
  await page.getByText('06 Timbavadi gate-Junagadh',{exact:true}).first().waitFor();
  const health = await (await page.request.get('http://127.0.0.1:8000/api/cameras/cam06/health')).json();
  if (health.streaming) {
    await page.waitForFunction(() => {
      const img=document.querySelector('img[alt="CCTV Stream cam06"]');
      return img && img.naturalWidth===1920 && img.naturalHeight===1080;
    },null,{timeout:20000});
    await page.getByAltText('CCTV Stream cam06').click();
    await page.waitForTimeout(2000);
    await page.screenshot({path:fileURLToPath(new URL('government-feed-gpu.png',folder)),fullPage:true});
  }
  await page.screenshot({path:fileURLToPath(new URL('current-live.png',folder)),fullPage:true});
  assert.equal(failures.length,0,failures.join('\n'));
  console.log('PASS: real browser opened local preview, registry contains 30 organizer cameras, Live Cameras renders, no JS exceptions.');
} finally {await browser.close();}
