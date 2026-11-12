<script setup>
import {computed} from 'vue'
import {t} from '../../preferences'
import ReviewDisclosure from '../office/ReviewDisclosure.vue'
import ReviewIssueList from '../office/ReviewIssueList.vue'
import ReviewMetadata from '../office/ReviewMetadata.vue'
import {docxReviews} from '../office/reviewModel'
const props=defineProps({document:Object,busy:Boolean,delegated:{type:Object,default:()=>({})},error:String})
const emit=defineEmits(['retry','locate','delegate'])
const view=computed(()=>docxReviews(props.document))
const groups=computed(()=>[view.value.deterministic,view.value.pages,view.value.document])
const summary=computed(()=>groups.value.some(g=>g.status==='issues')?'issues':groups.value.some(g=>g.status==='stale')?'stale':groups.value.some(g=>g.status==='unavailable')?'unavailable':groups.value.some(g=>g.status==='pending')?'pending':'passed')
</script>
<template>
 <section class="docx-quality" aria-label="Office quality review">
  <header><strong>{{ t('office.quality') }}</strong><span>R{{ document.revision }} · {{ t('office.state.'+summary) }}</span></header>
  <p class="office-review-meta">{{ document.selected_design?.id || t('docx.quality.template') }} · {{ t('docx.quality.repairs') }}: {{ document.repair_summary?.attempts || 0 }}</p>
  <p v-if="document.repair_summary?.revision===document.revision&&document.repair_summary.stop_reason">{{ t('docx.quality.repairStopped') }}: {{ t('docx.quality.stop.'+document.repair_summary.stop_reason) }}</p>
  <p v-if="error" role="alert">{{ error }}</p>
  <ReviewDisclosure v-for="group in groups" :key="document.document_id+':'+group.key" :data-office-group="group.key" :title="t('docx.quality.'+group.key)" :status="group.status" :kind="group.key==='deterministic'?'automatic':'visual'" :issues="group.issues">
   <p v-if="group.status==='stale'">{{ t('office.staleNote') }}</p>
   <template v-if="group.key==='pageVisual'">
    <p class="office-page-coverage">{{ group.reviewed }}/{{ group.total }} {{ t('office.pages') }}</p>
    <section v-for="page in group.reviews" :key="page.page" class="office-page-review" :data-review-page="page.page">
     <strong>{{ t('docx.page',{page:page.page}) }} · {{ t('office.state.'+page.status) }}</strong>
     <p v-if="page.raw?.summary">{{ page.raw.summary }}</p><ReviewMetadata v-if="page.raw" :review="page.raw" />
     <ReviewIssueList :issues="page.issues" :busy="busy" :delegated="delegated" @locate="emit('locate',$event)" @delegate="emit('delegate',$event)" />
    </section>
   </template>
   <template v-else>
    <p v-if="group.raw?.summary">{{ group.raw.summary }}</p>
    <ReviewMetadata v-if="group.raw" :review="group.raw" />
    <ReviewIssueList :issues="group.issues" :busy="busy" :delegated="delegated" @locate="emit('locate',$event)" @delegate="emit('delegate',$event)" />
   </template>
   <button v-if="group.key!=='deterministic'" type="button" class="text-button" :disabled="busy||view.deterministic.status!=='passed'" @click="emit('retry')">{{ t('office.retryVisual') }}</button>
  </ReviewDisclosure>
  <p class="office-review-meta">{{ t('docx.visualAdvisory') }}</p>
 </section>
</template>
<style scoped>.docx-quality{padding:8px 16px;border-bottom:1px solid var(--border);font-size:11px;max-height:48vh;overflow:auto;flex-shrink:0}.docx-quality>header{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.office-page-review{display:flex;flex-direction:column;gap:8px;padding-bottom:10px;border-bottom:1px solid var(--border)}.office-review-meta{font-size:10px;color:var(--text-muted)}.docx-quality p{overflow-wrap:anywhere}</style>
