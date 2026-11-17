<script setup lang="ts">
import { computed, ref } from 'vue'
import ProviderIcon from '@/components/ProviderIcon.vue'
import AppIcon from '@/components/AppIcon.vue'
import { tr } from '@/composables/preferences'
import type { ModelScope } from '@/utils/modelSettings'

interface Row {
  id: string
  provider: string
  model: string
  scope: ModelScope
}
const props = defineProps<{ rows: Row[]; admin: boolean }>()
defineEmits<{ edit: [provider: string, scope: ModelScope] }>()
const search = ref('')
const scope = ref<'all' | ModelScope>('all')
const filtered = computed(() => props.rows.filter(row => (scope.value === 'all' || row.scope === scope.value) && `${row.model} ${row.provider}`.toLowerCase().includes(search.value.trim().toLowerCase())))
const scopeLabel = (value: ModelScope) => tr(value === 'personal' ? '个人' : '全局')
</script>

<template>
  <section class="model-registry space-y-3" :aria-label="tr('模型清单')">
    <div class="filter-toolbar">
      <label class="search-field">
        <AppIcon name="search" />
        <input
          v-model="search"
          type="search"
          :placeholder="tr('搜索模型或服务商')"
          :aria-label="tr('搜索模型或服务商')"
        />
      </label>
      <select v-model="scope" class="select select-fit" :aria-label="tr('按范围筛选')">
        <option value="all">{{ tr('全部范围') }}</option>
        <option value="personal">{{ tr('个人') }}</option>
        <option value="global">{{ tr('全局') }}</option>
      </select>
    </div>
    <div class="card overflow-hidden">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{{ tr('模型') }}</th>
              <th>{{ tr('服务商') }}</th>
              <th class="scope-col">{{ tr('范围') }}</th>
              <th class="col-end">{{ tr('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filtered" :key="row.id">
              <td><strong class="model-name">{{ row.model }}</strong></td>
              <td>
                <span class="provider-cell"><ProviderIcon :provider="row.provider" :size="22" />{{ row.provider }}</span>
              </td>
              <td class="scope-col">{{ scopeLabel(row.scope) }}</td>
              <td class="col-end">
                <div v-if="admin || row.scope === 'personal'" class="row-actions">
                  <button type="button" @click="$emit('edit', row.provider, row.scope)">{{ tr('编辑') }}</button>
                </div>
                <span v-else class="readonly-label">{{ tr('只读') }}</span>
              </td>
            </tr>
            <tr v-if="!filtered.length">
              <td colspan="4" class="table-empty">
                {{ tr(rows.length ? '没有匹配的模型' : '暂无已配置模型，点击右上角新增模型。') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.model-name {
  display: block;
  min-width: 120px;
  max-width: 260px;
  overflow-wrap: anywhere;
  color: var(--color-ink);
  font-weight: 500;
}
.provider-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.scope-col {
  white-space: nowrap;
}
.readonly-label {
  color: var(--color-ink-faint);
  white-space: nowrap;
}
</style>
