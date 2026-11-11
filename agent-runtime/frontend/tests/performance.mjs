// Deterministic browser workload; no model/API key or production data required.
import {chromium} from 'playwright'
import {writeFile} from 'node:fs/promises'
const base=process.env.PERF_BASE_URL||'http://127.0.0.1:8083'
const embedded=process.env.PERF_EMBEDDED==='1'
const output=process.env.PERF_OUTPUT||'/workspace/frontend-performance.json'
const answer='# Reliability report\n\n'+('A bounded transaction preserves the committed document. **Revision checks** reject concurrent edits, while background review records advisory findings.\n\n').repeat(24)+'\n| Check | Result |\n| --- | --- |\n| Structure | Passed |\n| Layout | Passed |\n'
const events=[];let seq=0
for(let turn=0;turn<80;turn++){
 events.push({seq:++seq,type:'operation',operation:'message',text:`Review section ${turn+1}`,occurred_at:'2026-11-11T10:00:00Z'})
 events.push({seq:++seq,type:'assistant_started',message_id:`m${turn}`})
 events.push({seq:++seq,type:'assistant_completed',content:answer,message_id:`m${turn}`})
 events.push({seq:++seq,type:'result',status:'completed',output:answer})
}
events.push({seq:++seq,type:'operation',operation:'message',text:'Generate another section'})
events.push({seq:++seq,type:'assistant_started',message_id:'live'})
const session={id:'perf',model_id:'test/model',status:'running',messages:[{role:'user',content:'Performance fixture'}],permission_mode:'allow',sandbox_mode:'restricted',enabled_features:[],output_files:[],usage:{},event_seq:seq,updated_at:'2026-11-11T10:00:00Z'}
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']})
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}})
 const errors=[];page.on('pageerror',error=>errors.push(error.message))
 await page.addInitScript(()=>{window.EventSource=class{constructor(){window.perfSource=this}close(){}};window.perfLongTasks=[];new PerformanceObserver(list=>{window.perfLongTasks.push(...list.getEntries().map(e=>e.duration))}).observe({type:'longtask',buffered:true})})
 if(embedded){
  await page.addInitScript(()=>{localStorage.setItem('itam_token','local-performance-fixture');localStorage.setItem('itam_user',JSON.stringify({username:'fixture',roles:[],permissions:[]}))})
  await page.route(/\/agent\?session=perf$/,route=>route.fulfill({path:process.env.PERF_INDEX||new URL('../../../frontEnd/dist/index.html',import.meta.url).pathname}))
 }
 const requests=[]
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname.replace('/api/agent-runtime/api','/api');requests.push(path)
  let value={}
  if(path==='/api/tool-catalog'||path==='/api/features'||path.endsWith('/files'))value=[]
  else if(path==='/api/models'||path==='/api/models/options')value={default:'test/model',profiles:[{id:'test/model',model:'model',reasoning_efforts:[],input:['text']}],llm:{default:'test/model'},revision:0}
  else if(path==='/api/agent/sessions')value=[session]
  else if(path.endsWith('/journal'))value={events}
  else if(path==='/api/agent/sessions/perf')value=session
  await route.fulfill({json:value})
 })
 await page.goto(base+(embedded?'/agent?session=perf':'/?session=perf'))
 await page.locator('.assistant-message').last().waitFor()
 await page.waitForTimeout(200)
 const input=page.locator('.composer textarea')
 await page.evaluate(start=>{
  window.perfStreamTimer=setInterval(()=>window.perfSource?.onmessage?.({data:JSON.stringify({seq:++start,type:'assistant_delta',content:'Generating the next section. '.repeat(100+(start%50)),message_id:'live'})}),40)
 },seq)
 const samples=[]
 for(let attempt=0;attempt<3;attempt++){
  await input.fill('')
  const start=performance.now()
  await input.pressSequentially('performance input test',{delay:0})
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
  samples.push(Math.round((performance.now()-start)*100)/100)
 }
 const menu=[]
 for(let attempt=0;attempt<15;attempt++){
  const elapsed=await page.evaluate(async()=>{
   const start=performance.now()
   document.querySelector('.model-select').click()
   await new Promise(resolve=>requestAnimationFrame(resolve))
   if(!document.querySelector('.model-popover'))throw new Error('Menu did not open')
   return performance.now()-start
  })
  menu.push(Math.round(elapsed*100)/100)
  await page.evaluate(async()=>{
   document.querySelector('.model-select').click()
   await new Promise(resolve=>requestAnimationFrame(resolve))
  })
 }
 await page.evaluate(()=>clearInterval(window.perfStreamTimer))
 const result={embedded,menu_open_ms:menu,menu_open_median_ms:menu.toSorted((a,b)=>a-b)[7],workload:{turns:80,answer_characters:answer.length,input_characters:22,stream_interval_ms:40},typing_ms:samples,typing_median_ms:samples.toSorted((a,b)=>a-b)[1],long_tasks:await page.evaluate(()=>window.perfLongTasks),page_errors:errors,requests:requests.length}
 await writeFile(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result))
}finally{await browser.close()}
