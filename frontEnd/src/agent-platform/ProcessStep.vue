<script setup>
import {computed,ref,watch,nextTick,onMounted,inject} from 'vue'
import Icon from './Icon.vue'
import MarkdownContent from './MarkdownContent.vue'
import {t} from './preferences'
import {settledStatuses,subagentResult} from './conversation'
import {compactToolSummary,stepBody,elapsed,formatDuration} from './processView'
const props=defineProps({step:Object,actionLabel:Function,now:Number,collapseEpoch:Number})
const cancelBackground=inject('cancelBackground',null)
const complete=computed(()=>settledStatuses.has(props.step.status))
const expanded=ref(!complete.value&&!props.step.backgroundLive),viewport=ref(null),follow=ref(true),cancelling=ref(false)
let programmatic=false
const TOOL_ICONS={execute:'Terminal',task:'Bot',start_background_task:'Workflow',check_background_task:'ListChecks',cancel_background_task:'CircleStop',read_subagent_log:'ScrollText'}
// Delegations read as a brief and an answer, not as raw tool input/output.
const delegation=computed(()=>props.step.kind==='tool'&&['task','start_background_task'].includes(props.step.name))
const background=computed(()=>props.step.name==='start_background_task')
const running=computed(()=>props.step.status==='running'||props.step.backgroundLive)
const answer=computed(()=>delegation.value&&!running.value?subagentResult(props.step.finalOutput):'')
const content=computed(()=>expanded.value&&!delegation.value ? stepBody(props.step,t) : '')
const label=computed(()=>props.step.kind==='compaction'?t('process.compaction'):props.step.kind==='reasoning'?t('process.thinking'):props.step.kind==='summary'?t('process.summary'):props.step.kind==='progress'?t('process.progress'):props.step.kind==='notice'?t('subagent.notice'):props.actionLabel(props.step.name))
const icon=computed(()=>props.step.status==='failed'?'CircleAlert':props.step.status==='cancelled'||props.step.status==='interrupted'?'X':props.step.kind==='compaction'?'Minimize2':props.step.kind==='reasoning'?'Brain':props.step.kind==='notice'?'CornerDownRight':props.step.kind==='tool'?(TOOL_ICONS[props.step.name]||'Wrench'):'FileText')
const statusText=computed(()=>props.step.backgroundLive||(background.value&&props.step.status==='running')?t('process.status.background'):t('process.status.'+props.step.status))
const duration=computed(()=>formatDuration(elapsed(props.step.startedAt,props.step.endedAt,props.step.durationMs,props.now,!complete.value),t))
const compactSummary=computed(()=>compactToolSummary(props.step,t))
const resultSummary=computed(()=>{
  if (props.step.kind!=='compaction') return props.step.resultSummary
  if (props.step.status==='running') return ''
  const outcome=props.step.compactionStatus||'compacted'
  const key=`process.compaction.${outcome}`
  const label=t(key)!==key?t(key):t('process.compaction.compacted')
  if (props.step.usedTokens!=null&&props.step.windowTokens!=null&&props.step.windowTokens>0) {
    return `${label} · ${t('process.compaction.tokens',{used:props.step.usedTokens,window:props.step.windowTokens})}`
  }
  return label
})
function onScroll(){if(!programmatic&&viewport.value){const el=viewport.value;follow.value=el.scrollHeight-el.scrollTop-el.clientHeight<=4}}
function tail(){if(!viewport.value||!expanded.value||!follow.value)return;programmatic=true;viewport.value.scrollTop=viewport.value.scrollHeight;requestAnimationFrame(()=>programmatic=false)}
async function cancel(){if(!cancelBackground||cancelling.value)return;cancelling.value=true;try{await cancelBackground(props.step.background?.runId)}finally{cancelling.value=false}}
watch(()=>props.step.status,(status,previous)=>{if(status===previous)return;expanded.value=!settledStatuses.has(status)&&!props.step.backgroundLive})
watch(()=>props.collapseEpoch,()=>{if(complete.value)expanded.value=false})
watch(content,async()=>{await nextTick();tail()})
watch(expanded,async value=>{if(value){await nextTick();tail()}})
onMounted(tail)
</script>
<template>
 <li class="process-node" :class="{'process-node-error':step.status==='failed','process-node-background':step.backgroundLive}" :data-step-id="step.key" :data-step-status="step.status">
  <button type="button" class="process-node-icon" :class="{expanded}" :aria-expanded="expanded" :aria-label="label" @click="expanded=!expanded">
   <Icon :name="icon" :size="15" class="process-step-glyph" :class="{spin:step.status==='running'&&step.kind==='reasoning'}"/>
   <Icon name="ChevronDown" :size="12" class="process-chevron process-step-toggle" :class="{expanded}"/>
  </button>
  <div class="process-node-body">
   <button class="process-step-heading" type="button" :aria-expanded="expanded" @click="expanded=!expanded">
    <span class="process-step-name" :title="label">{{ label }}</span><span class="process-step-status" :class="[step.status,{background:step.backgroundLive}]"><i v-if="step.backgroundLive" class="background-pulse" aria-hidden="true"></i>{{ statusText }}</span><time class="process-step-duration">{{ duration }}</time>
    <span v-if="compactSummary" class="process-step-result compact-tool-summary" :title="compactSummary.title">
     <span class="compact-tool-text" :class="{ 'compact-tool-command': compactSummary.command }">{{ compactSummary.text }}</span>
     <span v-if="compactSummary.more" class="compact-tool-count">{{ compactSummary.more }}</span>
     <span v-if="compactSummary.removed" class="compact-tool-count removed">−{{ compactSummary.removed }}</span>
     <span v-if="compactSummary.added" class="compact-tool-count added">+{{ compactSummary.added }}</span>
    </span>
    <span v-else class="process-step-result" :title="step.subject||resultSummary">{{ resultSummary }}</span>
   </button>
   <div class="process-step-fold" :class="{expanded}" :inert="!expanded" :aria-hidden="!expanded"><div class="process-step-fold-inner">
    <div v-if="expanded&&delegation" class="subagent-detail">
     <section v-if="step.subject"><h5>{{ t('subagent.brief') }}</h5><p>{{ step.subject }}</p></section>
     <section v-if="running" class="subagent-live"><Icon name="LoaderCircle" :size="13" class="spin"/><span>{{ t(background?'subagent.backgroundRunning':'subagent.running') }}</span><code v-if="step.background?.runId">{{ step.background.runId.slice(0,8) }}</code><button v-if="background&&step.backgroundLive&&cancelBackground" type="button" class="text-button subagent-cancel" :disabled="cancelling" @click.stop="cancel"><Icon name="CircleStop" :size="13"/>{{ t('subagent.cancel') }}</button></section>
     <section v-if="answer"><h5>{{ t(step.status==='completed'?'subagent.answer':'subagent.outcome') }}</h5><MarkdownContent :content="answer"/></section>
    </div>
    <pre v-else-if="expanded" ref="viewport" class="process-step-content" :class="{'is-live':!complete}" :data-following="follow" tabindex="0" role="region" :aria-label="t('process.details',{name:label})" @scroll.passive="onScroll">{{ content }}</pre>
   </div></div>
  </div>
 </li>
</template>

<style scoped>
.compact-tool-summary { display: flex; align-items: baseline; gap: .5em; }
.compact-tool-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.compact-tool-command { white-space: pre; font-family: 'SFMono-Regular', Consolas, monospace; }
.compact-tool-count { flex-shrink: 0; font-variant-numeric: tabular-nums; }
.compact-tool-count.removed { color: var(--error-text); }
.compact-tool-count.added { color: var(--success-text); }
.process-node-icon {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  flex: 0 0 16px;
  width: 16px;
  padding: 8px 0 0;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}
.process-node-icon .process-step-glyph,
.process-node-icon .process-step-toggle {
  transition: opacity .14s ease, transform .18s ease;
}
.process-node-icon .process-step-toggle {
  position: absolute;
  top: 9px;
  left: 50%;
  margin: 0;
  opacity: 0;
  pointer-events: none;
  transform: translateX(-50%) rotate(-90deg);
}
.process-node-icon.expanded .process-step-toggle,
.process-node-icon:hover .process-step-toggle,
.process-node-icon:focus-visible .process-step-toggle {
  opacity: 1;
}
.process-node-icon.expanded .process-step-toggle {
  transform: translateX(-50%) rotate(0);
}
.process-node-icon.expanded .process-step-glyph,
.process-node-icon:hover .process-step-glyph,
.process-node-icon:focus-visible .process-step-glyph {
  opacity: 0;
}
.process-node-icon:focus-visible {
  outline: 2px solid var(--border-focus, var(--color-primary));
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
