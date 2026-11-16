<script setup>
import {computed,ref,watch,nextTick,onMounted,inject} from 'vue'
import Icon from './Icon.vue'
import MarkdownContent from './MarkdownContent.vue'
import {t} from './preferences'
import {settledStatuses,subagentResult} from './conversation'
import {stepBody,elapsed,formatDuration} from './processView'
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
const label=computed(()=>props.step.kind==='reasoning'?t('process.thinking'):props.step.kind==='summary'?t('process.summary'):props.step.kind==='progress'?t('process.progress'):props.step.kind==='notice'?t('subagent.notice'):props.actionLabel(props.step.name))
const icon=computed(()=>props.step.status==='failed'?'CircleAlert':props.step.status==='cancelled'||props.step.status==='interrupted'?'X':props.step.kind==='reasoning'?'Brain':props.step.kind==='notice'?'CornerDownRight':props.step.kind==='tool'?(TOOL_ICONS[props.step.name]||'Wrench'):'FileText')
const statusText=computed(()=>props.step.backgroundLive||(background.value&&props.step.status==='running')?t('process.status.background'):t('process.status.'+props.step.status))
const duration=computed(()=>formatDuration(elapsed(props.step.startedAt,props.step.endedAt,props.step.durationMs,props.now,!complete.value),t))
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
  <span class="process-node-icon"><Icon :name="icon" :size="15" :class="{spin:step.status==='running'&&step.kind==='reasoning'}"/></span>
  <div class="process-node-body">
   <button class="process-step-heading" type="button" :aria-expanded="expanded" @click="expanded=!expanded">
    <span class="process-step-name" :title="label">{{ label }}</span><span class="process-step-status" :class="[step.status,{background:step.backgroundLive}]"><i v-if="step.backgroundLive" class="background-pulse" aria-hidden="true"></i>{{ statusText }}</span><time class="process-step-duration">{{ duration }}</time><span class="process-step-result" :title="step.subject||step.resultSummary">{{ step.resultSummary }}</span><Icon name="ChevronDown" :size="12" class="process-chevron" :class="{expanded}"/>
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
