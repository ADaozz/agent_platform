// Real Vue panel regression, isolated from external model availability.
import assert from 'node:assert/strict'
import { mkdtemp, writeFile, rm } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from 'playwright'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const folder = await mkdtemp(path.join(root, '.quality-ui-'))
const port = 4322, base = `http://127.0.0.1:${port}`, name = path.basename(folder)
let browser, server
try {
  await writeFile(path.join(folder,'index.html'), '<html><body><div id="app"></div><script type="module" src="./main.js"></script></body></html>')
  await writeFile(path.join(folder,'main.js'), `import {createApp,h,ref} from 'vue';import Panel from '/src/features/docx/Panel.vue';
localStorage.setItem('locale','en');const events=ref([]);window.qualityEvent=update=>events.value=[...events.value,{seq:events.value.length+1,type:'document_checked',document_id:'research',...update}];
createApp({setup(){const session={id:'fixture'};return()=>h(Panel,{session,active:true,events:events.value})}}).mount('#app');`)
  server=spawn(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:root,stdio:'ignore'})
  const deadline=Date.now()+15000
  while(Date.now()<deadline){try{if((await fetch(base)).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM || '/usr/bin/chromium',args:['--no-sandbox']});const page=await browser.newPage({locale:'en-US'})
  await page.route('**/api/agent/sessions/fixture/documents',route=>route.fulfill({json:[]}))
  await page.goto(`${base}/${name}/index.html`);await page.waitForFunction(()=>window.qualityEvent)
  await page.evaluate(()=>window.qualityEvent({revision:4,path:'research.docx',pages:[],delivery:{revision:4,deterministic:'passed',page_visual:'pending',document_visual:'pending',reviewed_pages:0,total_pages:2}}))
  await page.locator('.docx-quality').waitFor()
  assert.match(await page.locator('.docx-quality').innerText(),/Deterministic layout: Passed/)
  assert.match(await page.locator('.docx-quality').innerText(),/Page visual review: Pending/)
  await page.evaluate(()=>window.qualityEvent({revision:4,delivery:{revision:4,deterministic:'passed',page_visual:'passed',document_visual:'issues',reviewed_pages:2,total_pages:2,status:'draft_visual_issues'},document_review:{revision:4,status:'issues',summary:'Inconsistent heading spacing across pages',issues:[{pages:[1,2],observation:'Heading spacing differs',suggestion:'Use the same named heading style'}]}}))
  await page.getByRole('button',{name:/Structure, layout and visual review/}).click()
  await page.getByText('Inconsistent heading spacing across pages',{exact:false}).waitFor()
  assert.match(await page.locator('.docx-quality').innerText(),/Document visual review: Issues/)
  await page.evaluate(()=>{window.qualityEvent({revision:5});window.qualityEvent({revision:4,finalized:true,delivery:{revision:4,deterministic:'passed',page_visual:'passed',document_visual:'passed'}})})
  await page.waitForFunction(()=>document.querySelector('.docx-quality').innerText.includes('R5'))
  assert.match(await page.locator('.docx-quality').innerText(),/Deterministic layout: Pending/)
  assert.doesNotMatch(await page.locator('.docx-quality').innerText(),/Inconsistent heading spacing/)
  console.log('DOCX quality UI: three independent states, global issues, revision invalidation passed')
} finally {await browser?.close();server?.kill('SIGTERM');await rm(folder,{recursive:true,force:true})}
