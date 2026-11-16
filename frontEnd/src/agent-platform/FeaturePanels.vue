<script setup>
import {ref,computed,defineAsyncComponent,watch,onMounted} from 'vue'
import Icon from './Icon.vue'
import {api} from './featureApi'
import FilePreview from './FilePreview.vue'
import {previewFeature} from './filePreview'
import {t} from './preferences'
const props=defineProps({session:Object,events:Array})
const emit=defineEmits(['open','context','error'])
const modules=import.meta.glob('./features/*/Panel.vue')
const components=Object.fromEntries(Object.entries(modules).map(([path,loader])=>[path.split('/')[2],defineAsyncComponent(loader)]))
const visibleFeatures=computed(()=>features.value.filter(f=>!props.session?.enabled_features || props.session.enabled_features.includes(f.id)))
const features=ref([]),active=ref(''),open=ref({}),contexts=ref({})
const catalogs=ref({}),fileRequest=ref(null),library=ref([]),libraryLoaded=ref(false)
const shellOpen=ref(false),shellError=ref(''),shellPath=ref('')
const previewFiles=computed(()=>{
 const available=new Set(visibleFeatures.value.map(f=>f.id)),files=new Map(),present=new Set(library.value.map(f=>f.path))
 for(const file of library.value){const feature=previewFeature(file.path);if(feature==='file'||available.has(feature))files.set(file.path,{...file,feature})}
 // Office catalogs keep documents the Agent deleted; only list what is still in files/.
 for(const [feature,values] of Object.entries(catalogs.value))if(available.has(feature))for(const file of values)if(!libraryLoaded.value||present.has(file.path))files.set(file.path,{...file,feature})
 return [...files.values()].sort((a,b)=>a.path.localeCompare(b.path))
})
// Newest previewable file in the session's files/ directory, for the page header shortcut.
const latestFile=computed(()=>{const previewable=new Set(previewFiles.value.map(f=>f.path));return library.value.filter(f=>previewable.has(f.path)).sort((a,b)=>(b.modified_at||0)-(a.modified_at||0))[0]||null})
const contentOpen=computed(()=>!!open.value[active.value])
const showShell=computed(()=>shellOpen.value&&!contentOpen.value)
async function loadFiles(){const id=props.session?.id;if(!id){library.value=[];return}try{const files=await api(`/agent/sessions/${id}/files`);if(props.session?.id===id){library.value=files;libraryLoaded.value=true}}catch(e){emit('error',e.message)}}
function openFile(path){
 const feature=previewFeature(path)
 if(!feature)return
 if(feature!=='file'&&!visibleFeatures.value.some(f=>f.id===feature)){
  // Still show a closable pane so the user is not stuck with a blank reservation.
  shellPath.value=path;shellError.value=t('artifacts.previewUnavailable');shellOpen.value=true
  active.value='';open.value={};fileRequest.value=null
  emit('open',true);emit('context',null);emit('error',shellError.value)
  return
 }
 shellPath.value=path;shellError.value='';shellOpen.value=true
 active.value=feature;emit('open',true);emit('context',null)
 fileRequest.value={path,feature,token:(fileRequest.value?.token||0)+1}
}
function closeShell(){
 shellOpen.value=false;shellError.value='';shellPath.value=''
 active.value='';open.value={};contexts.value={};fileRequest.value=null
 emit('open',false);emit('context',null)
}
function onPanelError(message){
 emit('error',message)
 // Keep a closable shell with the failure reason instead of an empty 48vw gap.
 if(shellOpen.value&&!contentOpen.value){
  shellError.value=message||t('artifacts.previewUnavailable')
  emit('open',true)
 }
}
async function reload(){try{features.value=(await api('/features')).filter(f=>f.installed&&f.enabled&&components[f.id]);if(active.value!=='file'&&!features.value.some(f=>f.id===active.value)){active.value='';emit('open',false);emit('context',null)}}catch(e){emit('error',e.message)}}
function setOpen(feature,value){
 open.value={...open.value,[feature]:value}
 if(value){active.value=feature;shellOpen.value=false;shellError.value=''}
 const anyOpen=Object.values(open.value).some(Boolean)||shellOpen.value
 emit('open',anyOpen)
 emit('context',anyOpen?(contexts.value[active.value]||null):null)
}
function setContext(feature,value){contexts.value={...contexts.value,[feature]:value};if(feature===active.value)emit('context',value)}
watch(()=>props.session?.id,()=>{closeShell();catalogs.value={};library.value=[];libraryLoaded.value=false;loadFiles()},{immediate:true})
watch(()=>props.events?.filter(e=>e.type==='output_files'||e.type==='tool_completed').at(-1)?.seq,loadFiles)
onMounted(reload)
defineExpose({reload,openFile,latestFile,close:closeShell})
</script>
<template>
 <component v-for="feature in visibleFeatures" :key="feature.id" :is="components[feature.id]" :session="session" :events="events" :active="active===feature.id" :files="previewFiles" :open-request="fileRequest?.feature===feature.id ? fileRequest : null" @catalog="catalogs[feature.id]=$event" @select-file="openFile" @open="setOpen(feature.id,$event)" @context="setContext(feature.id,$event)" @error="onPanelError" />
 <FilePreview :session="session" :active="active==='file'" :request="fileRequest?.feature==='file'?fileRequest:null" :files="previewFiles" :events="events" @select-file="openFile" @open="setOpen('file',$event)" />
 <aside v-if="showShell" class="docx-panel file-preview-panel" :aria-label="t('filePreview.title')">
  <header class="docx-panel-header">
   <strong class="preview-shell-name">{{ shellPath.split('/').pop() || t('filePreview.title') }}</strong>
   <button class="icon-button" type="button" :aria-label="t('filePreview.close')" @click="closeShell"><Icon name="X" :size="17"/></button>
  </header>
  <p class="file-preview-error" role="alert">{{ shellError || t('filePreview.loading') }}</p>
 </aside>
</template>

<style scoped>
.preview-shell-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500;font-size:13px}
.file-preview-error{padding:12px 16px;font-size:12px;color:var(--error-text)}
.docx-panel-header .icon-button{margin-left:auto}
</style>
