<script setup>
import {t} from '../../preferences'
defineProps({issues:{type:Array,default:()=>[]},busy:Boolean,delegated:{type:Object,default:()=>({})}})
const emit=defineEmits(['locate','delegate'])
function severityLabel(value){if(!value)return t('office.ungraded');const key='pptx.severity.'+value,label=t(key);return label===key?value:label}
</script>
<template><ul class="office-review-issues"><template v-for="(item,index) in issues" :key="item.key || item.id || index"><slot name="item" :item="item" :index="index"><li :data-issue-id="item.id" :data-stale="item.stale">
 <div class="office-issue-head"><strong>{{ severityLabel(item.severity) }}</strong><code>{{ item.category || t('office.unknown') }}</code><span>{{ t('office.confidence') }}: {{ item.confidence ?? t('office.unknown') }}</span></div>
 <p v-if="item.pages?.length">{{ t('office.pages') }}: {{ item.pages.join(', ') }}</p><code v-if="item.blockId">Block: {{ item.blockId }}</code>
 <p>{{ item.observation }}</p><p>{{ t('office.suggestion') }}: {{ item.suggestion || t('office.unknown') }}</p>
 <p v-if="item.stale">{{ t('office.state.stale') }}</p><p v-else-if="item.pages?.length&&!item.region" class="office-localization-note">{{ t('office.pageOnly') }}</p><p v-else-if="!item.pages?.length">{{ t('office.noLocation') }}</p>
 <div class="office-issue-actions"><button class="text-button" type="button" :disabled="item.stale||!item.pages?.length" @click="emit('locate',item)">{{ t('office.locate') }}</button><button class="text-button" type="button" :disabled="busy||item.stale||delegated[item.key]" @click="emit('delegate',item)">{{ delegated[item.key]?t('office.delegated'):t('office.delegate') }}</button></div>
 </li></slot></template></ul></template>
<style>.office-review-issues{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}.office-review-issues>li{border:1px solid var(--border);border-radius:6px;padding:9px;overflow-wrap:anywhere}.office-review-issues p{margin:5px 0}.office-issue-head,.office-issue-actions{display:flex;flex-wrap:wrap;gap:9px;align-items:center}.office-issue-head,.office-localization-note{font-size:10px;color:var(--text-muted)}.office-review-issues [data-stale=true]{opacity:.65}</style>
