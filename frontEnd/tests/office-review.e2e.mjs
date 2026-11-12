// Real Chromium and the platform's real Vue Office panels; Office responses
// are controlled fixtures, while actual rendered PNGs exercise the preview UI.
import assert from 'node:assert/strict'
import {mkdtemp,writeFile,readFile,rm,mkdir} from 'node:fs/promises'
import {spawn} from 'node:child_process'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright'
const frontend=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const repository=path.resolve(frontend,'..')
const source=path.join(frontend,'src','agent-platform')
const roots=[{name:'platform',root:frontend,prefix:'/src/agent-platform'}]
const output=path.join(frontend,'test-results','office-review');await mkdir(output,{recursive:true})
const png1=await readFile(path.join(repository,'agent-runtime/docx-ooxml-skill/examples/research-quality-acceptance/page-001.png'))
const png2=await readFile(path.join(repository,'agent-runtime/docx-ooxml-skill/examples/workflow-acceptance/academic-page.png'))
function document(){
 const pages=[{page:1,fingerprint:'p1',checks:{automatic_passed:true}},{page:2,fingerprint:'p2',checks:{automatic_passed:true}}]
 const review=(page,status,issues=[])=>({revision:14,page,document_id:'research',request_id:'q1',fingerprint:'p'+page,status,issues,model_id:'fixture/vision-model',prompt_version:'page-3',reviewed_at:1700000000,review_id:'page-review-'+page})
 return {document_id:'research',path:'research.docx',revision:14,quality_contract:2,finalized:false,preview_revision:14,preview_pages:2,pages,document_check:{revision:14,final:true,passed:true,collision_check_executed:true,pages,repair_targets:[],geometry:{block_regions:{'fig-008':[{page:2,source:'pdf_image_digest',coordinate_space:'normalized',bbox:[.2,.3,.25,.15]}]}}},visual_request:{eligible:true,revision:14,request_id:'q1',fingerprints:['p1','p2']},aesthetic_reviews:{'1':review(1,'passed'),'2':review(2,'issues',[{id:'fig-issue',block_id:'fig-008',category:'spacing',severity:'major',confidence:'high',observation:'Figure spacing is too small',suggestion:'Adjust only the figure spacing'},{id:'page-only',block_id:'unmapped',observation:'Body spacing needs inspection',suggestion:'Inspect the rendered page'}])},document_review:{revision:14,request_id:'q1',fingerprints:['p1','p2'],review_id:'document-review',status:'issues',model_id:'fixture/vision-model',prompt_version:'doc-2',reviewed_at:1700000001,summary:'Global rhythm needs review',issues:[{id:'global',pages:[1,2],observation:'Cross-page heading consistency',suggestion:'Use the selected named style'}]}}
}
function presentation(){
 const review=(n)=>({revision:7,automatic_passed:true,fingerprint:'s'+n,layout_issues:[],aesthetic_review:{revision:7,review_id:'slide-review-'+n,status:n===1?'failed':'passed',model_id:'fixture/vision-model',prompt_version:'pptx-1',reviewed_at:1700000000,issues:n===1?[{id:'vision1',severity:'major',category:'spacing',confidence:'high',observation:'PPTX spacing issue',reason:'Screenshot evidence',suggestion:'Adjust the listed element',element_ids:['title'],region:[.1,.2,.3,.2]}]:[]}})
 const slides=[1,2].map(n=>({slide_id:'s'+n,background:'FFFFFF',complex:false,elements:[{id:'title',type:'text',text:'Slide '+n,geometry:{x:.1,y:.2,w:.3,h:.2},style:{font_family:'Arial',font_size:20,color:'17324D'}}],review:review(n)}))
 return {presentation_id:'presentation',path:'presentation.pptx',revision:7,sha256:'deck-sha',manifest:{slides},deck_review:{revision:7,request_id:'whole-request',review_id:'whole-review',slide_fingerprints:{s1:'s1',s2:'s2'},sha256:'deck-sha',status:'failed',issues:[{id:'whole1',slides:[2],severity:'minor',category:'density',observation:'Deck density issue',suggestion:'Inspect slide two'}]}}
}
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']})
try{for(const [index,entry] of roots.entries()){
 const folder=await mkdtemp(path.join(entry.root,'.office-review-ui-')),port=4330+index,base=`http://127.0.0.1:${port}`
 let server,page
 try{
  await writeFile(path.join(folder,'index.html'),'<html><div id="app"></div><script type="module" src="./main.js"></script></html>')
  await writeFile(path.join(folder,'style.css'),await readFile(path.join(source,'style.css')))
  await writeFile(path.join(folder,'theme.css'),await readFile(path.join(source,'theme.css')))
  await writeFile(path.join(folder,'main.js'),`import {createApp,h,ref} from 'vue';import Docx from '${entry.prefix}/features/docx/Panel.vue';import Pptx from '${entry.prefix}/features/pptx/Panel.vue';import './style.css';
const events=ref([]),format=ref('docx'),session=ref({id:'fixture',status:'running'});window.officePush=update=>events.value=[...events.value,{seq:events.value.length+1,type:format.value==='docx'?'document_checked':'presentation_review',...update}];window.officeFormat=value=>{events.value=[];format.value=value};window.officeSession=(status,id='fixture')=>session.value={id,status};window.officeErrors=[];createApp({setup(){return()=>h(format.value==='docx'?Docx:Pptx,{session:session.value,events:events.value,active:true,onError:message=>window.officeErrors.push(message)})}}).mount('#app');`)
  server=spawn(process.execPath,[path.join(entry.root,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:entry.root,stdio:'ignore'})
  const deadline=Date.now()+20000
  while(Date.now()<deadline){try{if((await fetch(base)).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
  page=await browser.newPage({locale:'en-US',viewport:{width:1600,height:1000}})
  const errors=[],calls=[];page.on('pageerror',e=>{errors.push(e.message);console.error(entry.name,e.message)})
  page.on('response',r=>{if(r.status()>=400&&!r.url().includes('/agent/sessions/'))console.error(entry.name,r.status(),r.url())})
  let doc=document(),deck=presentation(),failSteer=true,failRetry=false
  await page.route('**/*',async route=>{
   const request=route.request(),url=new URL(request.url()),name=url.pathname
   if(name.endsWith('.png')&&name.includes('/documents/'))return route.fulfill({body:name.endsWith('002.png')?png2:png1,contentType:'image/png'})
   if(!name.includes('/agent/sessions/'))return route.continue()
   if(request.method()==='GET')return route.fulfill({json:[]})
   const body=request.postDataJSON();calls.push({name,body})
   if(name.endsWith('/actions/steer')&&failSteer){failSteer=false;return route.fulfill({status:503,json:{detail:'Queue unavailable'}})}
   if(name.endsWith('/actions/steer')&&failRetry){failRetry=false;return route.fulfill({status:503,json:{detail:'Agent is not accepting requests'}})}
   if(name.endsWith('/visual-review')||name.endsWith('/aesthetic-review'))throw new Error('Visual review must be requested from the Agent, not the host: '+name)
   if(name.endsWith('/aesthetic-decision')){
    deck.manifest.slides[0].review.aesthetic_review.issues[0].dismissed=true
    return route.fulfill({json:deck})
   }
   return route.fulfill({json:{status:'queued'}})
  })
  await page.addInitScript(()=>{localStorage.setItem('locale','en');localStorage.setItem('itam-locale','en');localStorage.setItem('itam-theme','light')})
  await page.goto(`${base}/${path.basename(folder)}/index.html`);await page.waitForFunction(()=>window.officePush)
  await page.evaluate(value=>window.officePush(value),doc)
  await page.locator('.docx-page-image>img').waitFor()
  const groups=page.locator('.docx-quality .office-review-disclosure')
  assert.equal(await groups.count(),3)
  for(const name of ['deterministic','pageVisual','documentVisual'])await page.locator(`[data-office-group="${name}"]>summary`).click()
  assert.equal(await page.locator('.docx-quality .office-review-disclosure[open]').count(),3)
  assert.equal(await page.locator('[data-office-group="deterministic"]').getAttribute('data-status'),'passed')
  // Page visual review follows the page shown in the stage.
  await page.locator('.docx-thumbnails>button[data-page="2"]').click()
  await page.locator('.docx-thumbnails>button.selected[data-page="2"]').waitFor()
  const issue=page.locator('[data-issue-id="fig-issue"]')
  await page.locator('.docx-preview-status>select').selectOption('width')
  await issue.getByRole('button',{name:'Locate issue',exact:true}).click()
  await page.locator('.docx-thumbnails>button.selected[data-page="2"]').waitFor()
  await page.locator('.docx-issue-region').waitFor()
  const region=await page.locator('.docx-issue-region').evaluate(el=>({left:el.style.left,top:el.style.top}))
  assert.deepEqual(region,{left:'20%',top:'30%'})
  await page.waitForFunction(()=>{const stage=document.querySelector('.docx-stage').getBoundingClientRect(),region=document.querySelector('.docx-issue-region').getBoundingClientRect(),center=(region.top+region.bottom)/2;return center>=stage.top&&center<=stage.bottom})
  await issue.getByRole('button',{name:'Ask the Agent to fix',exact:true}).click()
  await page.getByRole('alert').getByText('Queue unavailable').waitFor()
  await issue.getByRole('button',{name:'Ask the Agent to fix',exact:true}).click()
  await issue.getByRole('button',{name:'Sent to the Agent'}).waitFor()
  assert.equal(calls.at(-1).body.artifact.document_id,'research');assert.equal(calls.at(-1).body.artifact.revision,14);assert.equal(calls.at(-1).body.artifact.block_id,'fig-008')
  await page.evaluate(()=>window.officeSession('completed'))
  const fallback=page.locator('[data-issue-id="page-only"]')
  assert.match(await fallback.innerText(),/Severity not provided/)
  await fallback.getByRole('button',{name:'Locate issue',exact:true}).click();assert.equal(await page.locator('.docx-issue-region').count(),0)
  assert.match(await fallback.innerText(),/Page navigation only/)
  await fallback.getByRole('button',{name:'Ask the Agent to fix',exact:true}).click()
  await fallback.getByRole('button',{name:'Sent to the Agent'}).waitFor()
  assert.match(calls.at(-1).name,/messages$/);assert.match(calls.at(-1).body.text,/"revision": 14/)
  await page.evaluate(()=>window.officeSession('running'))
  await page.locator('[data-issue-id="global"]').getByRole('button',{name:'Ask the Agent to fix',exact:true}).click()
  await page.locator('[data-issue-id="global"]').getByRole('button',{name:'Sent to the Agent'}).waitFor()
  assert.deepEqual(calls.at(-1).body.artifact.pages,[1,2]);assert.equal(calls.at(-1).body.artifact.review_id,'document-review')
  assert(!calls.some(call=>call.name.endsWith('/review')),'Delegation must not approve a page')
  await page.screenshot({path:path.join(output,entry.name+'-docx.png')})
  await page.locator('[data-office-group="pageVisual"]').getByRole('button',{name:'Ask the Agent to review again'}).click()
  await page.locator('[data-office-group="pageVisual"] .pptx-review-details>button').getByText('Sent to the Agent').waitFor()
  assert.match(calls.at(-1).name,/actions\/steer$/);assert.equal(calls.at(-1).body.artifact.feature,'docx');assert.equal(calls.at(-1).body.artifact.revision,14)
  assert.match(calls.at(-1).body.text,/review-images/);assert.match(calls.at(-1).body.text,/submit-review/)
  // The Agent opens a fresh request for the same revision before submitting new reviews.
  doc={...doc,visual_request:{...doc.visual_request,request_id:'q2'},aesthetic_reviews:{},document_review:null}
  await page.evaluate(value=>window.officePush(value),doc)
  await page.waitForFunction(()=>!document.querySelector('[data-issue-id="fig-issue"]'))
  assert.equal(await page.locator('[data-office-group="pageVisual"]').getAttribute('data-status'),'pending')
  const late=document();await page.evaluate(value=>window.officePush(value),late)
  assert.equal(await page.locator('[data-issue-id="fig-issue"]').count(),0)
  const pendingHeader=await page.locator('.docx-panel>.docx-gate-note').first().innerText()
  const oldAccepted={document_id:'research',revision:14,type:'document_aesthetic_review',aesthetic_reviews:Object.fromEntries(Object.entries(late.aesthetic_reviews).map(([key,r])=>[key,{...r,status:'passed',issues:[]}])),document_review:{...late.document_review,status:'passed',issues:[]},delivery:{revision:14,status:'accepted',document_review:{...late.document_review,status:'passed',issues:[]}},delivery_status:'accepted',finalized:true}
  // The accepted q1 event intentionally has NO visual_request envelope.
  await page.evaluate(value=>window.officePush(value),oldAccepted)
  assert.equal(await page.locator('.docx-panel>.docx-gate-note').first().innerText(),pendingHeader)
  assert.equal(await page.locator('[data-office-group="pageVisual"]').getAttribute('data-status'),'pending')
  const unavail={...doc,aesthetic_reviews:{'1':{revision:14,page:1,request_id:'q2',fingerprint:'p1',status:'passed',issues:[]},'2':{revision:14,page:2,request_id:'q2',fingerprint:'p2',status:'unavailable',issues:[],error:{code:'agent_cannot_inspect',message:'Current model cannot view images'}}},document_review:{revision:14,request_id:'q2',fingerprints:['p1','p2'],status:'unavailable',error:{code:'provider_timeout'}}}
  await page.evaluate(value=>window.officePush(value),unavail)
  await page.waitForFunction(()=>document.querySelector('[data-office-group="pageVisual"]').dataset.status==='unavailable')
  await page.locator('[data-office-group="pageVisual"]').getByText('View error',{exact:true}).click()
  await page.getByText(/Current model cannot view images/).first().waitFor()
  failRetry=true;await page.locator('[data-office-group="pageVisual"]').getByRole('button',{name:'Ask the Agent to review again'}).click();await page.getByRole('alert').getByText('Agent is not accepting requests').waitFor()
  await page.evaluate(()=>window.officePush({document_id:'research',revision:15,pages:[]}))
  await page.waitForFunction(()=>document.querySelector('.docx-quality').textContent.includes('R15'))
  assert.equal(await page.locator('.docx-issue-region').count(),0)
  await page.evaluate(value=>window.officePush(value),late)
  assert.equal(await page.locator('[data-issue-id="fig-issue"]').count(),0)
  const latest=document();latest.revision=15;latest.preview_revision=14;latest.visual_request={...latest.visual_request,revision:15,request_id:'q3',fingerprints:['new-p1','new-p2']};latest.pages=latest.pages.map((p,i)=>({...p,fingerprint:'new-p'+(i+1)}));latest.document_check={...latest.document_check,revision:15,pages:latest.pages};latest.aesthetic_reviews=Object.fromEntries(Object.entries(latest.aesthetic_reviews).map(([n,r])=>[n,{...r,revision:15,request_id:'q3',fingerprint:'new-p'+n}]));latest.document_review=null
  await page.evaluate(value=>window.officePush(value),latest)
  await page.locator('[data-issue-id="fig-issue"]').getByRole('button',{name:'Locate issue',exact:true}).click()
  await page.getByRole('alert').getByText(/current revision preview is not ready/).waitFor()
  assert.equal(await page.locator('.docx-issue-region').count(),0)
  await page.evaluate(()=>window.officePush({document_id:'research',revision:15,preview_revision:15,preview_pages:2}))
  await page.waitForFunction(()=>document.querySelector('.docx-preview-status').textContent.includes('15'))
  await page.locator('[data-issue-id="fig-issue"]').getByRole('button',{name:'Locate issue',exact:true}).click()
  await page.locator('.docx-issue-region').waitFor()
  await page.evaluate(()=>{window.officeFormat('pptx');window.officeSession('running')})
  await page.evaluate(value=>window.officePush(value),deck)
  await page.locator('.pptx-panel').waitFor()
  await page.locator('.pptx-slide-reviews .office-review-disclosure>summary').nth(0).click()
  await page.locator('.pptx-slide-reviews .office-review-disclosure>summary').nth(1).click()
  await page.locator('.pptx-deck-review>summary').click()
  const finding=page.locator('.pptx-findings>li').filter({hasText:'PPTX spacing issue'})
  await finding.hover();await page.locator('.pptx-stage>.pptx-canvas .pptx-highlight').first().waitFor()
  const delegate=finding.locator('button').filter({hasText:/Ask the Agent|交给 Agent/}).first()
  await delegate.click();await page.waitForFunction(()=>document.querySelector('.pptx-findings').textContent.includes('Sent to the Agent'))
  assert.equal(calls.at(-1).body.artifact.feature,'pptx');assert.equal(calls.at(-1).body.artifact.slide_id,'s1')
  await page.screenshot({path:path.join(output,entry.name+'-pptx.png')})
  const ignore=finding.locator('button').filter({hasText:/Ignore|Dismiss|忽略/});await ignore.click()
  await page.waitForFunction(()=>!Array.from(document.querySelectorAll('.pptx-findings>li')).some(el=>el.textContent.includes('PPTX spacing issue')))
  assert.match(calls.at(-1).name,/aesthetic-decision$/)
  await page.locator('.pptx-deck-review li').filter({hasText:'Deck density issue'}).click()
  await page.locator('.pptx-thumbnails>button.selected').filter({hasText:/02/}).waitFor()
  assert.equal(await page.locator('.pptx-deck-review[open]').count(),1,'Document review must stay open while locating another page')
  await page.locator('.pptx-deck-review li').filter({hasText:'Deck density issue'}).getByRole('button',{name:'Ask the Agent to fix',exact:true}).click()
  await page.locator('.pptx-deck-review li').getByRole('button',{name:'Sent to the Agent'}).waitFor()
  assert.equal(calls.at(-1).body.artifact.slide_id,'s2');assert.equal(calls.at(-1).body.artifact.request_id,'whole-request')
  assert.deepEqual(errors,[])
  await writeFile(path.join(output,entry.name+'-results.json'),JSON.stringify({passed:true,browserErrors:errors,actions:calls.map(c=>({path:c.name,artifact:c.body.artifact}))},null,2))
  console.log(entry.name+': independent panels, provenance, page/region location, running/idle delegation, agent review requests/errors, stale fences, PPTX highlights/dismissal passed')
 }finally{await page?.close();server?.kill('SIGTERM');await rm(folder,{recursive:true,force:true})}
}}finally{await browser.close()}
