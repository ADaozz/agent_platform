// Reuse the main Agent's existing steering/message channels; no repair is executed here.
export async function delegateOfficeIssue(api,{session,artifact,issue,pages,text}) {
 if (!session?.id || !Number.isInteger(artifact?.revision)) throw new Error('Invalid Office delegation context')
 if (issue.stale) throw new Error('The review is stale; refresh before delegating')
 const details={...artifact,pages:pages||issue.pages||[],block_id:issue.blockId||null,issue_id:issue.id,review_id:issue.reviewId||null,request_id:issue.requestId||null,observation:issue.observation,suggestion:issue.suggestion}
 const message=text?`${text}\nOffice context: ${JSON.stringify(details,null,2)}`:`Office local repair request\n${JSON.stringify(details,null,2)}\nRe-read the current document status and plan before editing. Modify only the identified local content, preserve necessary content and unrelated pages, then render and recheck. This is an explicit user delegation; visual review itself is read-only.`
 const running=['running','queued'].includes(session.status)
 return api(`/agent/sessions/${encodeURIComponent(session.id)}/${running?'actions/steer':'messages'}`,{method:'POST',body:running?{text:message,artifact:details}:{text:message}})
}
export function delegationKey({feature,identity,revision,requestId,issueId,pages}) {return JSON.stringify([feature,identity,revision,requestId||null,issueId,pages||[]])}
