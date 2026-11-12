// Presentation-only view models. Acceptance remains a server decision.
export function normalizeStatus(value) {
 if (['passed','pass'].includes(value)) return 'passed'
 if (['failed','fail','issues','blocked','needs_attention','needs_repair','uncertain','needs_verification'].includes(value)) return 'issues'
 if (value === 'stale') return 'stale'
 if (['unavailable','error'].includes(value)) return 'unavailable'
 return 'pending'
}
const same = (a,b) => JSON.stringify(a) === JSON.stringify(b)
export function reviewState(raw, valid = true) {
 if (!raw) return 'pending'
 if (!valid || raw.status === 'stale') return 'stale'
 if (raw.error) return 'unavailable'
 if ((raw.issues || []).some(i => !i.dismissed)) return 'issues'
 return normalizeStatus(raw.status)
}
export function normalizedRegion(region) {
 const values=Array.isArray(region)?region:region?.coordinate_space==='normalized'?region.bbox:null
 return values?.length===4 && values.every(Number.isFinite) && values[0]>=0 && values[1]>=0 && values[2]>0 && values[3]>0 && values[0]+values[2]<=1.000001 && values[1]+values[3]<=1.000001 ? values : null
}
export function issueView(raw,index,context) {
 const pages=(raw.pages || (raw.page ? [raw.page] : context.page ? [context.page] : [])).filter(p=>Number.isInteger(p)&&p>0&&p<=context.totalPages)
 const evidence=context.regions?.[raw.block_id]?.filter(r=>r.page===pages[0]&&['pdf_text_exact','pdf_image_digest'].includes(r.source))||[]
 const region=pages.length===1&&evidence.length===1?normalizedRegion(evidence[0]):null
 return {id:String(raw.id || raw.target_id || index),key:`${context.scope}:${raw.id||raw.target_id||index}`,raw,
  revision:context.revision,requestId:context.requestId,reviewId:context.reviewId,pages,blockId:raw.block_id || null,
  observation:raw.observation || (typeof raw.detail==='string'?raw.detail:raw.detail?JSON.stringify(raw.detail):raw.code || raw.type || ''),
  suggestion:raw.suggestion || null,severity:raw.severity || null,category:raw.category || raw.code || raw.type || null,confidence:raw.confidence ?? null,
  region,stale:context.stale,scope:context.scope,dismissed:raw.dismissed===true}
}
export function docxReviews(document) {
 const revision=document.revision,pages=document.pages||[],request=document.visual_request||{},modern=document.quality_contract>=2
 const scope=`docx:${document.document_id}:${revision}:${request.request_id||'legacy'}`
 const context={scope,revision,requestId:request.request_id,totalPages:pages.length}
 const check=document.document_check
 const checkCurrent=check?.revision===revision&&(check.passed===false||!modern||pages.length>0&&Array.isArray(check.pages)&&same(check.pages.map(p=>p.fingerprint),pages.map(p=>p.fingerprint)))
 context.regions=checkCurrent?check?.geometry?.block_regions:null
 const deterministic={key:'deterministic',raw:check,status:!check?'pending':!checkCurrent?'stale':check.passed===false?'issues':check.passed===true&&check.final&&(!modern||check.collision_check_executed)?'passed':'pending',issues:[]}
 deterministic.issues=(check?.repair_targets||[]).map((i,n)=>issueView(i,n,{...context,scope:scope+':deterministic',stale:!checkCurrent})).map(i=>({...i,pageFingerprints:pages.map(p=>p.fingerprint)}))
 const requestCurrent=pages.length>0&&(!modern || (request.eligible && (!request.document_id||request.document_id===document.document_id) && request.revision===revision && same(request.fingerprints,pages.map(p=>p.fingerprint))))
 const pageReviews=pages.map(page=>{
  const raw=document.aesthetic_reviews?.[String(page.page)]
  const valid=!!(requestCurrent&&raw?.revision===revision&&(!raw.document_id||raw.document_id===document.document_id)&&(raw.page===undefined||raw.page===page.page)&&raw.fingerprint===page.fingerprint&&(!modern || (request.request_id && raw.request_id===request.request_id)))
  const state=reviewState(raw,valid)
  return {page:page.page,raw,status:state,issues:(raw?.issues||[]).map((i,n)=>issueView(i,n,{...context,scope:scope+':page:'+page.page+':'+(raw?.review_id||''),reviewId:raw?.review_id,page:page.page,stale:!valid})),fingerprint:page.fingerprint}
 })
 const states=pageReviews.map(p=>p.status)
 const pageStatus=!states.length?'pending':states.includes('stale')?'stale':states.includes('pending')?'pending':states.includes('unavailable')?'unavailable':states.includes('issues')?'issues':'passed'
 const overall=document.document_review
 const overallValid=!!(requestCurrent&&overall?.revision===revision&&(!overall.document_id||overall.document_id===document.document_id)&&same(overall.fingerprints,pages.map(p=>p.fingerprint))&&(!modern||(request.request_id&&overall.request_id===request.request_id)))
 return {scope,revision,deterministic,pages:{key:'pageVisual',status:pageStatus,reviewed:pageReviews.filter(p=>!['pending','stale'].includes(p.status)).length,total:pages.length,reviews:pageReviews,issues:pageReviews.flatMap(p=>p.issues)},
  document:{key:'documentVisual',raw:overall,status:reviewState(overall,overallValid),issues:(overall?.issues||[]).map((i,n)=>issueView(i,n,{...context,scope:scope+':document:'+(overall?.review_id||''),reviewId:overall?.review_id,stale:!overallValid}))}}
}
export function pptxReviews(deck,slide) {
 const review=slide?.review||{},visual=review.aesthetic_review,whole=deck?.deck_review,slides=deck?.manifest?.slides||[]
 const carried=review.revision<deck?.revision&&review.automatic_passed===true&&!!review.fingerprint&&slide?.formal?.revision===review.revision&&(review.review_design_sha256||null)===(deck?.manifest?.review_design?.sha256||null)
 const current=review.revision===deck?.revision||carried
 const visualCurrent=current&&(!review.request_id||review.request_id===visual?.request_id)&&(visual?.revision===undefined||visual.revision===review.revision)&&(!visual?.slide_id||visual.slide_id===slide?.slide_id)&&(!visual?.presentation_id||visual.presentation_id===deck?.presentation_id)&&(!visual?.fingerprint||visual.fingerprint===review.fingerprint)
 const wholeCurrent=slides.length>0&&whole?.revision===deck?.revision&&!!whole.request_id&&(!whole.sha256||whole.sha256===deck.sha256)&&!!whole.slide_fingerprints&&same(Object.keys(whole.slide_fingerprints).sort(),slides.map(s=>s.slide_id).sort())&&slides.every(s=>s.review?.fingerprint===whole.slide_fingerprints[s.slide_id])
 return {automatic:!review.revision&&review.revision!==0?'pending':!current?'stale':review.render_error?'unavailable':review.automatic_passed===true?'passed':review.automatic_passed===false?'issues':'pending',visual:reviewState(visual,visualCurrent),document:reviewState(whole,wholeCurrent),visualCurrent,wholeCurrent,carried}
}
