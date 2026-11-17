<template>
  <div class="devices">
    <div class="header">
      <span class="title">电视列表</span>
      <el-button size="small" @click="$emit('logout')">登出</el-button>
    </div>

    <el-button size="small" type="primary" style="width: 100%; margin-bottom: 8px" @click="showAdd = true">
      添加电视
    </el-button>

    <el-scrollbar height="62vh">
      <el-card
        v-for="d in devices"
        :key="d.id"
        class="dev"
        :class="{ active: d.id === current }"
        @click="$emit('select', d)"
      >
        <div class="row">
          <b>{{ d.name || d.id.slice(0, 8) }}</b>
          <span class="actions">
            <el-tag :type="truthy(d.online) ? 'success' : 'info'" size="small">
              {{ truthy(d.online) ? '在线' : '离线' }}
            </el-tag>
            <el-button size="small" type="danger" text @click.stop="remove(d)">删除</el-button>
          </span>
        </div>
      </el-card>
      <el-empty v-if="!devices.length" description="还没有电视" />
    </el-scrollbar>

    <el-dialog v-model="showAdd" title="添加电视" width="440px">
      <el-input v-model="newName" placeholder="设备名，如 客厅电视" />
      <el-alert v-if="newToken" type="success" :closable="false" style="margin-top: 12px">
        <div>令牌（仅显示一次，请填入电视端）：</div>
        <code class="token">{{ newToken }}</code>
      </el-alert>
      <template #footer>
        <el-button @click="showAdd = false">关闭</el-button>
        <el-button type="primary" @click="add">生成令牌</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { createDevice, deleteDevice } from '../api'

defineProps({
  devices: { type: Array, default: () => [] },
  current: { type: String, default: '' },
})
const emit = defineEmits(['select', 'logout', 'refresh'])

const showAdd = ref(false)
const newName = ref('')
const newToken = ref('')

function truthy(v) {
  return v === 1 || v === true
}

async function add() {
  const d = await createDevice(newName.value || 'TV')
  newToken.value = d.token
  emit('refresh')
}

async function remove(d) {
  const label = d.name || d.id.slice(0, 8)
  if (!confirm(`删除「${label}」？`)) return
  await deleteDevice(d.id)
  emit('refresh')
}
</script>

<style scoped>
.devices { padding: 12px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.title { font-weight: 600; }
.dev { margin-bottom: 8px; cursor: pointer; }
.dev.active { border-color: var(--el-color-primary); }
.row { display: flex; justify-content: space-between; align-items: center; }
.actions { display: flex; align-items: center; gap: 4px; }
.token { word-break: break-all; }
</style>
