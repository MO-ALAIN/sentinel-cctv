import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';

const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const base='http://127.0.0.1:8011/dashboard/';
async function navigate(label){await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:label,exact:true}).click();}
async function noHorizontalOverflow(){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'Page must fit the viewport');}
try {
  await page.goto(base);
  await page.getByRole('heading',{name:'What would you like to do?',exact:true}).waitFor();
  for(let i=1;i<=12;i++) {
    const response=await page.request.post('http://127.0.0.1:8011/api/registry/cameras',{data:{id:`NAV-${i}`,name:`Navigation fixture ${i}`,location:'Synthetic pagination test',source_type:'RECORDED'}});
    assert.equal(response.status(),200);
  }
  await page.getByRole('button',{name:'More tools',exact:true}).waitFor();
  assert.equal(await page.getByRole('navigation').getByRole('button',{name:'Traffic analytics',exact:true}).isVisible(),false);
  await noHorizontalOverflow();
  await page.screenshot({path:fileURLToPath(new URL('../docs/verification/organized-home-fixture.png',import.meta.url)),fullPage:true});
  for(const [label,id] of [['Live Cameras','cameras'],['Find vehicle','vehicle-trace'],['Alerts','live-alerts'],['Watchlist','watchlist'],['Camera registry','gis']]) {
    await navigate(label);await page.waitForURL(`${base}#${id}`);
    await noHorizontalOverflow();
  }
  await page.getByRole('button',{name:'Coverage',exact:true}).click();
  await page.getByRole('button',{name:'Measure coverage',exact:true}).waitFor();
  await page.getByRole('button',{name:'Imports & reports',exact:true}).click();
  for(const label of ['Export','Gap report','Audit history','Import organizer catalogue']) await page.getByRole('button',{name:label,exact:true}).waitFor();
  await page.getByRole('button',{name:'Camera list & map',exact:true}).click();
  assert.equal(await page.locator('.police-table-wrap:visible tbody tr').count(),10);
  const firstCamera=await page.locator('.police-table-wrap:visible tbody tr').first().innerText();
  await page.getByRole('button',{name:'Next',exact:true}).click();
  assert.notEqual(await page.locator('.police-table-wrap:visible tbody tr').first().innerText(),firstCamera);
  await page.getByRole('button',{name:'Previous',exact:true}).click();
  await page.getByRole('button',{name:'Show map',exact:true}).click();
  assert.equal(await page.locator('.geo-map:visible').count(),1);
  await navigate('Live Cameras');
  await page.getByRole('button',{name:'Next cameras',exact:true}).click();
  await page.getByRole('button',{name:'Previous cameras',exact:true}).click();
  await page.getByLabel('Search live cameras').fill('NAV-12');
  await page.getByText('Navigation fixture 12',{exact:true}).waitFor();
  await page.getByRole('button',{name:'More tools',exact:true}).click();
  for(const [label,id] of [['Monitoring dashboard','dashboard'],['Traffic analytics','analytics'],['Incident review','incidents'],['Connection management','camera-management'],['Plate-reading assessment','anpr-assessment'],['Recorded demos','demo'],['System status','system-status']]) {
    await navigate(label);await page.waitForURL(`${base}#${id}`);await page.waitForTimeout(400);
    assert.ok(await page.locator('main').innerText(),`Page ${id} should render`);
  }
  // The former global demo mode must no longer override other pages.
  await navigate('Recorded demos');await navigate('Find vehicle');
  await page.getByLabel('Vehicle registration').waitFor();
  await page.goBack();await page.waitForURL(`${base}#demo`);
  await page.goForward();await page.getByLabel('Vehicle registration').waitFor();
  await page.reload();await page.getByLabel('Vehicle registration').waitFor();
  await page.getByRole('button',{name:'Collapse navigation',exact:true}).click();
  await navigate('Overview');await page.getByRole('heading',{name:'What would you like to do?',exact:true}).waitFor();
  await page.getByRole('button',{name:'Expand navigation',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await noHorizontalOverflow();
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await page.screenshot({path:fileURLToPath(new URL('../docs/verification/organized-mobile-menu.png',import.meta.url))});
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('button',{name:'Open navigation',exact:true}).getAttribute('aria-expanded'),'false');
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();await navigate('Camera registry');
  await page.getByRole('heading',{name:'Camera registry & GIS',exact:true}).waitFor();await noHorizontalOverflow();
  await page.screenshot({path:fileURLToPath(new URL('../docs/verification/organized-mobile-registry.png',import.meta.url)),fullPage:true});
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASS: all 13 pages remain reachable; registry tools, map, browser history, direct links, demo independence, collapsed navigation and mobile menu work.');
} finally {await browser.close();}
