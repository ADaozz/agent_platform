<script setup>
import { computed, ref } from 'vue'
import { t } from '../../preferences'
const props = defineProps({ document: Object })
const emit = defineEmits(['retry'])
const open = ref(false)
const delivery = computed(() => props.document?.delivery?.revision === props.document?.revision ? props.document.delivery : {})
const statuses = computed(() => [
  ['deterministic', delivery.value.deterministic || 'pending'],
  ['pageVisual', delivery.value.page_visual || 'pending'],
  ['documentVisual', delivery.value.document_visual || 'pending']
])
const reviews = computed(() => Object.values(props.document?.aesthetic_reviews || {}).filter(r => r.revision === props.document.revision))
const overall = computed(() => props.document?.document_review?.revision === props.document?.revision ? props.document.document_review : null)
</script>
<template>
  <section class="docx-quality" aria-live="polite">
    <div class="docx-quality-statuses"><span v-for="[kind, status] in statuses" :key="kind" :data-status="status">{{ t('docx.quality.' + kind) }}: <strong>{{ t('docx.quality.' + status) }}</strong></span></div>
    <button type="button" class="text-button" :aria-expanded="open" @click="open = !open">{{ t('docx.workflowStatus') }} · {{ delivery.reviewed_pages || 0 }}/{{ delivery.total_pages || 0 }} · R{{ document.revision }}</button>
    <div v-if="open" class="docx-quality-details">
      <p>{{ document.selected_design?.id || t('docx.quality.template') }} · {{ t('docx.quality.repairs') }}: {{ delivery.repair_attempts || 0 }}</p>
      <p v-if="document.repair_summary?.revision === document.revision && document.repair_summary?.stop_reason">{{ t('docx.quality.repairStopped') }}: {{ t('docx.quality.stop.' + document.repair_summary.stop_reason) }}</p>
      <p v-if="delivery.status && delivery.status !== 'accepted'">{{ t('docx.quality.' + delivery.status) }}</p>
      <p v-for="(issue, i) in delivery.unresolved || []" :key="i">{{ issue.page || '—' }} · {{ issue.block_id || '' }} · {{ issue.code }} · {{ typeof issue.detail === 'string' ? issue.detail : '' }}</p>
      <div v-for="review in reviews" :key="review.review_id || review.page"><p>{{ t('docx.page', {page:review.page}) }} · {{ t('docx.quality.' + (['failed', 'uncertain'].includes(review.status) ? 'issues' : review.status)) }} · {{ review.summary }}</p><p v-if="review.error">{{ review.error.code }}: {{ review.error.message }}</p><p v-for="(issue,i) in review.issues" :key="i">{{ issue.block_id || '' }} {{ issue.observation }} — {{ issue.suggestion }}</p></div>
      <div v-if="overall"><p>{{ t('docx.quality.documentVisual') }} · {{ overall.summary }}</p><p v-if="overall.error">{{ overall.error.code }}: {{ overall.error.message }}</p><p v-for="(issue,i) in overall.issues" :key="i">{{ issue.pages.join(', ') }} · {{ issue.observation }} — {{ issue.suggestion }}</p></div>
      <button v-if="delivery.deterministic === 'passed'" class="text-button" type="button" @click="emit('retry')">{{ t('docx.quality.retry') }}</button>
      <p>{{ t('docx.visualAdvisory') }}</p>
    </div>
  </section>
</template>
<style scoped>
.docx-quality{padding:8px 16px;border-bottom:1px solid var(--border);font-size:11px}.docx-quality-statuses{display:flex;gap:6px 14px;flex-wrap:wrap}.docx-quality-statuses [data-status="failed"],.docx-quality-statuses [data-status="issues"]{color:var(--error-text)}.docx-quality-details{max-height:240px;overflow:auto}.docx-quality-details p{margin:8px 0;overflow-wrap:anywhere}
</style>
