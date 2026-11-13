<script setup lang="ts">
// @ts-ignore: the workspace UI is reused as-is from agent-runtime (JavaScript SFCs)
import AgentPlatform from '@/agent-platform/AgentPlatform.vue'
// @ts-ignore
import { theme } from '@/agent-platform/preferences'
import '@/agent-platform/style.css'
// Visual layer on top of the shared workspace styles; keeps src/agent-platform in sync with agent-runtime.
import '@/styles/agent-workspace.css'
import WorkspaceBackdrop from '@/components/WorkspaceBackdrop.vue'
</script>

<template>
  <div class="dap-root agent-host" :data-theme="theme">
    <AgentPlatform>
      <template #backdrop><WorkspaceBackdrop /></template>
    </AgentPlatform>
  </div>
</template>

<style scoped>
/* Fixed-position parts of the workspace (sidebar, modals, panels) anchor to this box instead of the viewport. */
.agent-host {
  --dap-vh: calc(100dvh - 3.5rem);
  position: relative;
  height: var(--dap-vh);
  overflow: hidden;
  contain: layout paint;
  color-scheme: light;
}
.agent-host[data-theme='dark'] {
  color-scheme: dark;
}
/* Conversation navigation lives in the platform sidebar, so the workspace reserves no sidebar column.
   The shared styles reserve one on narrow screens with !important (expanded / document-open states). */
.agent-host :deep(.shell),
.agent-host :deep(.shell.expanded),
.agent-host :deep(.shell.document-open) {
  --sidebar-width: 0px !important;
}
/* The standalone app scrolled the document; embedded, its main column scrolls instead. */
.agent-host :deep(main) {
  height: var(--dap-vh);
  overflow-y: auto;
  isolation: isolate;
  --ws-backdrop-gutter: 24px;
  --ws-backdrop-top: 0px;
  --ws-backdrop-bottom: 0px;
}
/* Match existing content gutters and preview bounds without changing either. */
.agent-host :deep(main.session-layout),
.agent-host :deep(.document-open > main) {
  --ws-backdrop-gutter: 0px;
}
.agent-host :deep(main:has(> .page-header)) {
  --ws-backdrop-top: 52px;
}
@media (max-width: 700px) {
  .agent-host :deep(.document-open > main) {
    --ws-backdrop-bottom: 44dvh;
  }
}
@media (max-width: 600px) {
  .agent-host :deep(main) {
    --ws-backdrop-gutter: 0px;
  }
}
</style>
