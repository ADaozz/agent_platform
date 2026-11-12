<script setup>
import {computed} from 'vue'
import {t} from '../../preferences'
import ReviewDisclosure from '../office/ReviewDisclosure.vue'
import ReviewIssueList from '../office/ReviewIssueList.vue'
import ReviewMetadata from '../office/ReviewMetadata.vue'
import {docxReviews} from '../office/reviewModel'
const props=defineProps({document:Object,page:Number,busy:Boolean,requested:Boolean,delegated:{type:Object,default:()=>({})},error:String})
const emit=defineEmits(['retry','locate','delegate'])
const view=computed(()=>docxReviews(props.document))
const groups=computed(()=>[view.value.deterministic,view.value.pages,view.value.document])
const currentPage=computed(()=>view.value.pages.reviews.find(review=>review.page===props.page)||null)
// Deterministic layout issues follow the page in the stage, like the per-slide automatic check in PPTX.
const pageChecks=computed(()=>view.value.deterministic.issues.filter(issue=>issue.pages.includes(props.page)))
const shownGroups=computed(()=>groups.value.map(group=>group.key==='pageVisual'?{...group,status:currentPage.value?.status||'pending',issues:currentPage.value?.issues||[]}:group.key==='deterministic'?{...group,status:group.status==='issues'&&!pageChecks.value.length?'passed':group.status,issues:pageChecks.value}:group))
const summary=computed(()=>groups.value.some(g=>g.status==='issues')?'issues':groups.value.some(g=>g.status==='stale')?'stale':groups.value.some(g=>g.status==='unavailable')?'unavailable':groups.value.some(g=>g.status==='pending')?'pending':'passed')
</script>
<template>
 <section class="docx-quality" aria-label="Office quality review">
  <header><strong>{{ t('office.quality') }}</strong><span>R{{ document.revision }} · {{ t('office.state.'+summary) }}</span></header>
  <p class="office-review-meta">{{ document.selected_design?.id || t('docx.quality.template') }} · {{ t('docx.quality.repairs') }}: {{ document.repair_summary?.attempts || 0 }}</p>
  <p v-if="document.repair_summary?.revision===document.revision&&document.repair_summary.stop_reason">{{ t('docx.quality.repairStopped') }}: {{ t('docx.quality.stop.'+document.repair_summary.stop_reason) }}</p>
  <p v-if="error" role="alert">{{ error }}</p>
  <ReviewDisclosure v-for="group in shownGroups" :key="document.document_id+':'+group.key" :data-office-group="group.key" :title="t('docx.quality.'+group.key)" :status="group.status" :kind="group.key==='deterministic'?'automatic':'visual'" :issues="group.issues">
   <p v-if="group.status==='stale'">{{ t('office.staleNote') }}</p>
   <template v-if="group.key==='pageVisual'">
    <section v-if="currentPage" class="office-page-review" :data-review-page="currentPage.page">
     <p v-if="currentPage.raw?.summary">{{ currentPage.raw.summary }}</p><ReviewMetadata v-if="currentPage.raw" :review="currentPage.raw" />
     <ReviewIssueList :issues="currentPage.issues" :busy="busy" :delegated="delegated" @locate="emit('locate',$event)" @delegate="emit('delegate',$event)" />
    </section>
   </template>
   <template v-else-if="group.key==='deterministic'">
    <p v-for="item in group.issues" :key="item.key" :data-issue-id="item.id" :class="'docx-check-issue docx-check-'+(item.severity||'ungraded')"><span>{{ item.severity||t('office.ungraded') }}</span> {{ item.category||t('office.unknown') }}<template v-if="item.blockId"> · {{ item.blockId }}</template><template v-if="item.observation"> — {{ item.observation }}</template></p>
   </template>
   <template v-else>
    <p v-if="group.raw?.summary">{{ group.raw.summary }}</p>
    <ReviewMetadata v-if="group.raw" :review="group.raw" />
    <ReviewIssueList :issues="group.issues" :busy="busy" :delegated="delegated" @locate="emit('locate',$event)" @delegate="emit('delegate',$event)" />
   </template>
   <button v-if="group.key!=='deterministic'" type="button" class="text-button" :disabled="busy||requested||view.deterministic.status!=='passed'" @click="emit('retry')">{{ requested?t('office.delegated'):t('office.retryVisual') }}</button>
  </ReviewDisclosure>
  <p class="office-review-meta">{{ t('docx.visualAdvisory') }}</p>
 </section>
</template>
<style scoped>.docx-quality{align-self:stretch;margin-top:18px;font-size:11px;flex-shrink:0;min-width:0;color-scheme:normal}.docx-quality>header{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.office-page-review{display:flex;flex-direction:column;gap:8px;padding-bottom:10px;border-bottom:1px solid var(--border)}.office-review-meta{font-size:10px;color:var(--text-muted)}.docx-quality p{overflow-wrap:anywhere}.docx-check-error>span{color:var(--error-text)}.docx-check-warning>span{color:var(--warning-text)}.docx-check-advisory>span,.docx-check-ungraded>span{color:var(--text-secondary)}</style>
