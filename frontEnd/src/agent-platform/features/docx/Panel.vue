<script setup>
import {ref,computed,watch} from 'vue'
import Icon from '../../Icon.vue'
import PreviewFileSelect from '../../PreviewFileSelect.vue'
import DocxPreview from './DocxPreview.vue'
import QualityReview from './QualityReview.vue'
import {docxReviews} from '../office/reviewModel'
import {delegateOfficeIssue,requestOfficeReview} from '../office/delegate'
import {t} from '../../preferences'
import {mergeDocument,previewKey} from './state'
import {api} from '../../featureApi'
import {API_BASE} from '../../runtime'
const props=defineProps({session:Object,events:{type:Array,default:()=>[]},active:Boolean,files:{type:Array,default:()=>[]},openRequest:Object})
const emit=defineEmits(['open','context','error','catalog','select-file'])
const selected=computed(()=>props.session)
async function guard(fn){try{return await fn()}catch(error){emit('error',error.message)}}
const documents = ref({}), activeDocumentId = ref(''), documentOpen = ref(false), renderedRevision = ref(null)
const preview=ref(null), reviewBusy=ref(false), reviewError=ref(''), delegatedIssues=ref({}), reviewRequested=ref(false)
let documentEpoch=0
const activeDocument = computed(() => documents.value[activeDocumentId.value])
const documentUrl = computed(() => activeDocument.value && selected.value ? `${API_BASE}/agent/sessions/${selected.value.id}/documents/${encodeURIComponent(activeDocumentId.value)}/revisions/${activeDocument.value.revision}` : '')
const documentStorageKey = computed(() => previewKey(selected.value?.id, activeDocumentId.value))
function receiveDocuments(updates) {
  documentEpoch++
  for (const event of updates) {
    if (!event.document_id || !Number.isInteger(event.revision)) continue
    const previous = documents.value[event.document_id]
    const next = mergeDocument(previous, event)
    if (next === previous) continue
    documents.value = { ...documents.value, [event.document_id]: next }
    if (!previous) {
      activeDocumentId.value = event.document_id
      documentOpen.value = sessionStorage.getItem(previewKey(selected.value?.id, event.document_id) + ':closed') !== 'true'
    }
  }
}
function receiveSnapshots(values,epoch){receiveDocuments(values.filter(value=>epoch===documentEpoch||!documents.value[value.document_id]||documents.value[value.document_id].revision<value.revision))}
watch(documents,values=>emit('catalog',Object.values(values).filter(file=>file.path)))
watch(()=>props.openRequest,async request=>{
 if(!request||!props.session)return
 const id=props.session.id
 await guard(async()=>{
  const epoch=documentEpoch
  const values=await api(`/agent/sessions/${id}/documents`)
  if(props.session?.id!==id||props.openRequest?.token!==request.token)return
  receiveSnapshots(values,epoch)
  const document=Object.values(documents.value).find(file=>file.path===request.path)
  if(!document)throw new Error(t('artifacts.previewUnavailable'))
  activeDocumentId.value=document.document_id;showDocument()
 })
},{immediate:true})
function closeDocument() { documentOpen.value = false; sessionStorage.setItem(documentStorageKey.value + ':closed', 'true') }
function showDocument() { documentOpen.value = true; emit('open',true); sessionStorage.removeItem(documentStorageKey.value + ':closed') }
function feedbackContext() { return activeDocument.value ? { document_id: activeDocumentId.value, revision: renderedRevision.value ?? activeDocument.value.revision } : null }
watch(activeDocumentId, () => { renderedRevision.value = null })
function currentScope(){return `${selected.value?.id}:${activeDocumentId.value}:${activeDocument.value?.revision}:${activeDocument.value?.visual_request?.request_id||''}`}
function currentIssue(item){
 if(!activeDocument.value)return null
 const view=docxReviews(activeDocument.value)
 return [view.deterministic,...view.pages.reviews,view.document].flatMap(g=>g.issues).find(i=>i.key===item.key&&!i.stale)
}
function locateIssue(item){
 const issue=currentIssue(item),page=item.selectedPage||issue?.pages[0]
 if(!issue||!issue.pages.includes(page)){reviewError.value=t('office.staleNote');return}
 const fingerprint=activeDocument.value.pages?.find(p=>p.page===page)?.fingerprint
 if(!preview.value?.locate({revision:activeDocument.value.revision,page,fingerprint,blockId:issue.blockId,region:issue.region}))reviewError.value=t('office.previewNotCurrent')
 else reviewError.value=''
}
async function delegateIssue(item){
 const issue=currentIssue(item),scope=currentScope(),session={...selected.value},identity=activeDocumentId.value,revision=activeDocument.value?.revision
 if(!issue){reviewError.value=t('office.staleNote');return}
 reviewBusy.value=true;reviewError.value=''
 try{
  await delegateOfficeIssue(api,{session,text:t('office.fixRequest',{observation:issue.observation,suggestion:issue.suggestion||t('office.unknown')}),artifact:{feature:'docx',document_id:activeDocumentId.value,revision:activeDocument.value.revision},issue})
  if(currentScope()===scope)delegatedIssues.value={...delegatedIssues.value,[issue.key]:true}
 }catch(error){if(currentScope()===scope)reviewError.value=error.message}
 finally{if(selected.value?.id===session.id&&activeDocumentId.value===identity&&activeDocument.value?.revision===revision)reviewBusy.value=false}
}
async function retryVisualReview() {
 const session={...selected.value},identity=activeDocumentId.value,revision=activeDocument.value.revision,path=activeDocument.value.path
 const scope=currentScope();reviewBusy.value=true;reviewError.value=''
 try{
  await requestOfficeReview(api,{session,artifact:{feature:'docx',document_id:identity,revision,path},text:t('office.reviewRequest',{path})})
  if(currentScope()===scope)reviewRequested.value=true
 }catch(error){if(currentScope()===scope)reviewError.value=error.message}
 finally{if(selected.value?.id===session.id&&activeDocumentId.value===identity&&activeDocument.value?.revision===revision)reviewBusy.value=false}
}
watch(()=>currentScope(),()=>{delegatedIssues.value={};reviewError.value='';reviewRequested.value=false})
watch(()=>`${selected.value?.id}:${activeDocumentId.value}:${activeDocument.value?.revision}`,()=>{reviewBusy.value=false})
function resetDocuments() { renderedRevision.value = null; documents.value = {}; activeDocumentId.value = ''; documentOpen.value = false }

let cursor=0
watch(()=>props.session?.id,async id=>{
 resetDocuments();cursor=0
 if(!id)return
 receiveDocuments(props.events.filter(e=>e.type.startsWith('document_')))
 cursor=props.events.at(-1)?.seq||0
 const epoch=documentEpoch
 await guard(async()=>{const values=await api(`/agent/sessions/${id}/documents`);if(props.session?.id===id)receiveSnapshots(values,epoch)})
},{immediate:true})
watch(()=>props.events.at(-1)?.seq,()=>{
 const batch=props.events.filter(e=>e.seq>cursor);cursor=props.events.at(-1)?.seq||cursor
 receiveDocuments(batch.filter(e=>e.type.startsWith('document_')))
})
watch(()=>[documentOpen.value,activeDocumentId.value],()=>emit('open',documentOpen.value&&!!activeDocument.value))
watch(()=>[activeDocument.value?.revision,renderedRevision.value,props.active],()=>emit('context',activeDocument.value?{feature:'docx',...feedbackContext()}:null))
</script>
<template>
    <button v-if="activeDocument && (!documentOpen || !active)" type="button" class="docx-reopen secondary" @click="showDocument"><Icon name="FileText" :size="15" />{{ activeDocument.path }}</button>
    <aside v-if="activeDocument && documentOpen && active" class="docx-panel" :aria-label="t('docx.preview')">
      <header class="docx-panel-header"><Icon name="FileText" :size="17" /><PreviewFileSelect :model-value="activeDocument.path" :files="files" @update:model-value="emit('select-file',$event)" /><a :href="documentUrl" download :aria-label="t('Download')"><Icon name="Download" :size="17" /></a><button type="button" class="icon-button" :aria-label="t('docx.close')" @click="closeDocument"><Icon name="X" :size="17" /></button></header>
      <p class="docx-gate-note">{{ activeDocument.finalized ? t('docx.finalized') : t('docx.draft') }}</p>
      <p v-if="activeDocument.external_conflict" class="docx-gate-error">{{ t('docx.externalConflict') }}</p>
      <p v-if="activeDocument.preview_error" class="docx-gate-error">{{ t('docx.previewUnavailable') }}</p>
      <p v-if="activeDocument.render_error" class="docx-gate-error" role="alert">{{ t('docx.checkFailed') }} {{ activeDocument.render_error }}</p>      <DocxPreview ref="preview" :key="selected.id + activeDocumentId" :revision="activeDocument.revision" :render-revision="activeDocument.preview_revision" :render-pages="activeDocument.preview_pages" :page-hashes="activeDocument.preview_page_hashes" :render-base-url="`${API_BASE}/agent/sessions/${selected.id}/documents/${encodeURIComponent(activeDocumentId)}/renders`" :image-base-url="`${API_BASE}/agent/sessions/${selected.id}/documents/${encodeURIComponent(activeDocumentId)}/page-images`" :pages="activeDocument.pages || []" :storage-key="documentStorageKey" @rendered="renderedRevision = $event" v-slot="{ page }"><QualityReview :document="activeDocument" :page="page" :busy="reviewBusy" :requested="reviewRequested" :error="reviewError" :delegated="delegatedIssues" @retry="retryVisualReview" @locate="locateIssue" @delegate="delegateIssue" /></DocxPreview>
    </aside>
</template>
