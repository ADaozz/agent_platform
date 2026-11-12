// Revisions and review-request generations fence asynchronous snapshots/events.
export function mergeDocument(previous, update) {
 if (!update?.document_id || !Number.isInteger(update.revision)) return previous
 if (previous && update.revision < previous.revision) return previous
 const newer=!previous||update.revision>previous.revision
 const retired=newer?[]:[...(previous._retired_review_requests||[])]
 const incoming=update.visual_request?.request_id,old=previous?.visual_request?.request_id
 if(!newer&&incoming&&retired.includes(incoming))return previous
 const changed=!newer&&Object.hasOwn(update,'visual_request')&&incoming!==old
 if(changed&&old)retired.push(old)
 // Delivery flags and review objects are one request-owned snapshot. A late
 // event may omit visual_request, so bind it using ALL available result IDs.
 const requestForUpdate=Object.hasOwn(update,'visual_request')?incoming:old
 let scoped=update
 if(!newer&&(old||incoming||retired.length)){
  const reviews=[...Object.values(update.aesthetic_reviews||{}),update.document_review,update.delivery?.document_review].filter(Boolean)
  const ids=[incoming,update.request_id,update.delivery?.request_id,...reviews.map(r=>r.request_id)].filter(id=>id!==undefined&&id!==null)
  const bound=requestForUpdate&&ids.length>0&&ids.every(id=>id===requestForUpdate)
  const wrongReview=reviews.some(r=>r.request_id!==requestForUpdate||(r.revision!==undefined&&r.revision!==update.revision))
  if(!bound||wrongReview){
   scoped={...update}
   for(const key of ['aesthetic_reviews','document_review','delivery','delivery_status','finalized','request_id'])delete scoped[key]
  }
 }
 const resetRequest=changed?{request_id:incoming||null,aesthetic_reviews:{},document_review:null,delivery:null,delivery_status:incoming?'draft_pending_visual':'draft_pending_check',finalized:false}:{}
 const next={...(previous||{}),...(newer?{pages:[],request_id:null,finalized:false,render_error:null,document_check:null,aesthetic_reviews:{},document_review:null,visual_request:null,delivery:null,delivery_status:'draft_pending_check'}:{}),...resetRequest,...scoped,_retired_review_requests:retired}
 const request=next.visual_request?.request_id
 if(!newer&&!changed&&scoped.aesthetic_reviews){
  const valid=Object.fromEntries(Object.entries(scoped.aesthetic_reviews).filter(([,r])=>!request||r.request_id===request))
  next.aesthetic_reviews={...(previous.aesthetic_reviews||{}),...valid}
 }
 if(!newer&&scoped.document_review&&request&&scoped.document_review.request_id!==request)next.document_review=previous.document_review
 return next
}
export function previewKey(sessionId, documentId) { return `docx-preview:${sessionId}:${documentId}` }
