import './browser-environment.mjs';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage();let fail=true;const errors=[];page.on('pageerror',e=>errors.push(e.message));
try {
 await page.route('**/api/cameras/anpr-status',route=>route.fulfill({status:fail?503:200,contentType:'application/json',body:JSON.stringify(fail?{detail:'Assessment test unavailable'}:{cameras:[]})}));
 await page.goto('http://127.0.0.1:8000/dashboard/#anpr-assessment');
 await page.getByRole('alert').filter({hasText:'Assessment test unavailable'}).waitFor();
 assert.equal(await page.locator('tbody tr').count(),0);
 assert.equal(await page.getByText('5 CLASSES ACTIVE',{exact:false}).count(),0);
 fail=false;await page.getByRole('button',{name:'Refresh results',exact:true}).click();
 await page.getByText('No camera assessment has been run in this process.',{exact:false}).waitFor();
 assert.equal(await page.locator('tbody tr').count(),0);assert.equal(errors.length,0);
 console.log('PASS: failed and empty assessments show no fabricated measurements; retry recovers.');
} finally {await browser.close();}
