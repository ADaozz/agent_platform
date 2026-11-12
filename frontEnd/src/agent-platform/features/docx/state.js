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
 const next={...(previous||{}),...(newer?{pages:[],finalized:false,render_error:null,document_check:null,aesthetic_reviews:{},document_review:null,visual_request:null,delivery:null,delivery_status:'draft_pending_check'}:{}),...update,_retired_review_requests:retired}
 const request=next.visual_request?.request_id
 if(!newer&&!changed&&update.aesthetic_reviews){
  const valid=Object.fromEntries(Object.entries(update.aesthetic_reviews).filter(([,r])=>!request||r.request_id===request))
  next.aesthetic_reviews={...(previous.aesthetic_reviews||{}),...valid}
 }
 if(!newer&&update.document_review&&request&&update.document_review.request_id!==request)next.document_review=previous.document_review
 return next
}
export function previewKey(sessionId, documentId) { return `docx-preview:${sessionId}:${documentId}` }
