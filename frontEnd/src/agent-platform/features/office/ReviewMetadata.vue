<script setup>
import {ref} from 'vue'
import {t} from '../../preferences'
defineProps({review:Object})
const rawOpen=ref(false)
function timestamp(value){if(value===undefined||value===null||value==='')return t('office.unknown');const date=new Date(typeof value==='number'?value*1000:value);return Number.isNaN(date.valueOf())?t('office.unknown'):date.toLocaleString()}
</script>
<template><div class="office-review-meta">
 <span>{{ t('office.model') }}: {{ review?.model_id || t('office.unknown') }}</span>
 <span>{{ t('office.prompt') }}: {{ review?.prompt_version || t('office.unknown') }}</span>
 <span>{{ t('office.reviewedAt') }}: {{ timestamp(review?.reviewed_at ?? review?.created_at) }}</span>
 <span>{{ t('office.rawStatus') }}: {{ review?.status ?? (typeof review?.passed==='boolean'?'passed='+review.passed:t('office.unknown')) }}</span>
 <span v-if="review?.revision !== undefined">R{{ review.revision }}</span>
 <span>Request: {{ review?.request_id || t('office.unknown') }}</span>
 <span>Review: {{ review?.review_id || t('office.unknown') }}</span>
</div><details v-if="review?.checks"><summary>{{ t('office.checkEvidence') }}</summary><pre>{{ JSON.stringify(review.checks,null,2) }}</pre></details><details v-if="review?.error || review?.render_error" class="office-review-error"><summary>{{ t('office.viewError') }}</summary><pre>{{ typeof (review.error||review.render_error)==='string'?(review.error||review.render_error):JSON.stringify(review.error||review.render_error,null,2) }}</pre></details><details @toggle="rawOpen=$event.target.open"><summary>{{ t('office.rawReview') }}</summary><pre v-if="rawOpen">{{ JSON.stringify(review,null,2) }}</pre></details></template>
<style scoped>.office-review-meta{display:flex;gap:5px 12px;flex-wrap:wrap;color:var(--text-muted);font-size:10px;overflow-wrap:anywhere}.office-review-error pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px}</style>
