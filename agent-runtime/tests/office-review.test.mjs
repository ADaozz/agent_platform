import test from 'node:test'
import assert from 'node:assert/strict'
const roots=['../frontend/src/features','../../frontEnd/src/agent-platform/features']
for(const root of roots){
 const {docxReviews,pptxReviews,normalizeStatus}=await import(root+'/office/reviewModel.js')
 const {delegateOfficeIssue,delegationKey}=await import(root+'/office/delegate.js')
 const {mergeDocument}=await import(root+'/docx/state.js')
 const source=()=>({document_id:'d',revision:4,quality_contract:2,pages:[{page:1,fingerprint:'a'},{page:2,fingerprint:'b'}],document_check:{revision:4,passed:true,final:true,collision_check_executed:true,pages:[{fingerprint:'a'},{fingerprint:'b'}]},visual_request:{eligible:true,revision:4,request_id:'q',fingerprints:['a','b']},aesthetic_reviews:{'1':{page:1,revision:4,request_id:'q',fingerprint:'a',status:'passed',issues:[]},'2':{page:2,revision:4,request_id:'q',fingerprint:'b',status:'issues',issues:[{block_id:'fig',observation:'Spacing',suggestion:'Check spacing'}]}},document_review:{revision:4,request_id:'q',fingerprints:['a','b'],status:'passed',issues:[]}})
 test(root+' normalizes statuses conservatively',()=>{
  assert.equal(normalizeStatus('failed'),'issues');assert.equal(normalizeStatus('uncertain'),'issues');assert.equal(normalizeStatus('stale'),'stale');assert.equal(normalizeStatus('invented'),'pending')
 })
 test(root+' keeps independent states and does not invent severity',()=>{
  const view=docxReviews(source());assert.equal(view.deterministic.status,'passed');assert.equal(view.pages.status,'issues');assert.equal(view.document.status,'passed')
  assert.equal(view.pages.issues[0].severity,null);assert.equal(view.pages.issues[0].confidence,null);assert.equal(view.pages.issues[0].region,null)
 })
 test(root+' refuses stale revision, request and pixels despite an accepted delivery flag',()=>{
  for(const mutation of [r=>r.revision=3,r=>r.request_id='old',r=>r.fingerprint='wrong']){
   const doc=source();doc.delivery={status:'accepted',revision:4};mutation(doc.aesthetic_reviews['1']);assert.equal(docxReviews(doc).pages.reviews[0].status,'stale')
  }
  const doc=source();doc.document_check.pages[0].fingerprint='wrong';assert.equal(docxReviews(doc).deterministic.status,'stale')
  doc.document_review.fingerprints.reverse();assert.equal(docxReviews(doc).document.status,'stale')
 })
 test(root+' distinguishes unavailable, pending and model uncertainty',()=>{
  const doc=source();doc.aesthetic_reviews['2'].status='unavailable';doc.aesthetic_reviews['2'].issues=[];assert.equal(docxReviews(doc).pages.status,'unavailable')
  delete doc.aesthetic_reviews['2'];assert.equal(docxReviews(doc).pages.status,'pending')
 })
 test(root+' only uses verified block coordinates from the bound deterministic render',()=>{
  const doc=source();doc.document_check.geometry={block_regions:{fig:[{page:2,source:'pdf_image_digest',coordinate_space:'normalized',bbox:[.1,.2,.3,.4]}]}}
  assert.deepEqual(docxReviews(doc).pages.issues[0].region,[.1,.2,.3,.4])
  doc.document_check.geometry.block_regions.fig[0].source='model_guess';assert.equal(docxReviews(doc).pages.issues[0].region,null)
  doc.aesthetic_reviews['2'].issues[0].region={coordinate_space:'normalized',bbox:[.1,.2,.3,.4]};assert.equal(docxReviews(doc).pages.issues[0].region,null)
 })
 test(root+' request generations fence late same-revision results',()=>{
  let doc=mergeDocument(null,source());doc=mergeDocument(doc,{document_id:'d',revision:4,visual_request:{...doc.visual_request,request_id:'new'},aesthetic_reviews:{},document_review:null})
  assert.equal(mergeDocument(doc,source()),doc)
  doc=mergeDocument(doc,{document_id:'d',revision:4,aesthetic_reviews:source().aesthetic_reviews,document_review:source().document_review})
  assert.deepEqual(doc.aesthetic_reviews,{});assert.equal(doc.document_review,null)
 })
 test(root+' PPTX validates bound page/whole results and preserves raw advice',()=>{
  const slide={slide_id:'s',review:{revision:4,fingerprint:'fp',automatic_passed:true,aesthetic_review:{revision:4,status:'failed',issues:[{severity:'major',element_ids:['title']}]}}}
  const deck={revision:4,presentation_id:'p',manifest:{slides:[slide]},deck_review:{revision:4,request_id:'r',slide_fingerprints:{s:'fp'},status:'passed',issues:[]}}
  assert.equal(pptxReviews(deck,slide).visual,'issues');assert.equal(pptxReviews(deck,slide).document,'passed')
  deck.deck_review.slide_fingerprints.s='other';assert.equal(pptxReviews(deck,slide).document,'stale')
  slide.review.aesthetic_review.revision=3;assert.equal(pptxReviews(deck,slide).visual,'stale')
  assert.deepEqual(slide.review.aesthetic_review.issues[0].element_ids,['title'])
 })
 test(root+' missing fingerprints and unavailable integrity cannot be shown as passed',()=>{
  const doc=source();doc.pages.forEach(p=>delete p.fingerprint);doc.document_check.pages.forEach(p=>delete p.fingerprint);doc.visual_request.fingerprints=[null,null]
  assert.notEqual(docxReviews(doc).deterministic.status,'passed')
  const slide={review:{revision:4,automatic_passed:true,fingerprint:'fp',visual_integrity:{status:'unavailable'}}}
  assert.equal(pptxReviews({revision:4,manifest:{slides:[slide]}},slide).automatic,'unavailable')
  delete slide.review.fingerprint;delete slide.review.visual_integrity;assert.notEqual(pptxReviews({revision:4},slide).automatic,'passed')
 })
 test(root+' empty page inventories cannot fabricate a passed review',()=>{
  const doc=source();doc.pages=[];doc.document_check.pages=[];doc.visual_request.fingerprints=[];doc.document_review.fingerprints=[]
  const view=docxReviews(doc);assert.notEqual(view.deterministic.status,'passed');assert.notEqual(view.document.status,'passed')
  const deck={revision:4,manifest:{slides:[]},deck_review:{revision:4,request_id:'q',status:'passed',slide_fingerprints:{}}}
  assert.notEqual(pptxReviews(deck,null).document,'passed')
 })
 test(root+' only reuses a retained unchanged PPTX render with matching design evidence',()=>{
  const slide={slide_id:'s',formal:{revision:3},review:{revision:3,automatic_passed:true,fingerprint:'fp',review_design_sha256:'design',aesthetic_review:{revision:3,status:'passed',issues:[]}}}
  const deck={revision:4,manifest:{slides:[slide],review_design:{sha256:'design'}}}
  assert.equal(pptxReviews(deck,slide).carried,true);assert.equal(pptxReviews(deck,slide).visual,'passed')
  slide.review.review_design_sha256='different';assert.equal(pptxReviews(deck,slide).visual,'stale')
 })
 test(root+' delegates to the existing running or idle Agent with version context',async()=>{
  const calls=[],api=async(...args)=>{calls.push(args);return {}}
  for(const status of ['running','completed'])await delegateOfficeIssue(api,{session:{id:'session',status},artifact:{feature:'docx',document_id:'d',revision:4},issue:{id:'i',blockId:'fig',pages:[2],observation:'Spacing',suggestion:'Local correction'}})
  assert.match(calls[0][0],/actions\/steer$/);assert.match(calls[1][0],/messages$/)
  assert.equal(calls[0][1].body.artifact.block_id,'fig');assert.match(calls[1][1].body.text,/"revision": 4/)
  await assert.rejects(delegateOfficeIssue(api,{session:{id:'s'},artifact:{revision:5},issue:{stale:true}}),/stale/)
  assert.equal(calls.length,2)
  assert.notEqual(delegationKey({revision:4,issueId:'i'}),delegationKey({revision:5,issueId:'i'}))
 })
}

test('both shipped frontends keep the shared Office implementation in sync',async()=>{
 const {readFile}=await import('node:fs/promises')
 for(const file of ['office/reviewModel.js','office/delegate.js','office/ReviewDisclosure.vue','office/ReviewIssueList.vue','office/ReviewMetadata.vue','docx/QualityReview.vue','docx/DocxPreview.vue','docx/state.js','pptx/ReviewDisclosure.vue','pptx/SlideCanvas.vue']){
  const contents=await Promise.all(roots.map(root=>readFile(new URL(root+'/'+file,import.meta.url),'utf8')))
  assert.equal(contents[0],contents[1],file)
 }
})
