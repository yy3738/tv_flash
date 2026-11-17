<template>
  <div class="remote">
    <div class="toolbar">
      <el-tag :type="online ? 'success' : 'danger'">{{ online ? '在线' : '离线' }}</el-tag>
      <el-button size="small" @click="reqSnapshot">截屏</el-button>
      <el-button size="small" @click="key('back')">返回</el-button>
      <el-button size="small" @click="key('home')">主页</el-button>
      <el-button size="small" @click="key('vol_up')">音量 +</el-button>
      <el-button size="small" @click="key('vol_down')">音量 -</el-button>
      <el-button size="small" type="danger" plain @click="kick">断开</el-button>
    </div>

    <div ref="screenEl" class="screen" @click="onClick">
      <img v-if="imgUrl" :src="imgUrl" class="shot" />
      <el-empty v-else description="点击“截屏”查看画面" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { RemoteSocket } from '../ws'
import { kickDevice } from '../api'

const props = defineProps({ device: { type: Object, required: true } })
const emit = defineEmits(['refresh'])

const online = ref(props.device.online === 1 || props.device.online === true)
const imgUrl = ref('')
const screenEl = ref(null)
let sock = null

function handle(msg) {
  if (msg.kind === 'binary') {
    const buf = msg.data
    if (buf.byteLength > 1 && new Uint8Array(buf)[0] === 0x01) {
      const blob = new Blob([buf.slice(1)], { type: 'image/jpeg' })
      if (imgUrl.value) URL.revokeObjectURL(imgUrl.value)
      imgUrl.value = URL.createObjectURL(blob)
    }
    return
  }
  const d = msg.data
  if (d.type === 'device_status') online.value = !!d.online
}

onMounted(async () => {
  sock = new RemoteSocket(handle)
  try {
    await sock.connect()
    sock.openSession(props.device.id)
    reqSnapshot()
  } catch (e) {
    online.value = false
  }
})

onBeforeUnmount(() => {
  if (sock) sock.close()
  if (imgUrl.value) URL.revokeObjectURL(imgUrl.value)
})

function reqSnapshot() {
  if (sock) sock.send({ type: 'snapshot_request', deviceId: props.device.id })
}

function key(k) {
  if (sock) sock.send({ type: 'system_key', deviceId: props.device.id, key: k })
}

function onClick(ev) {
  const img = screenEl.value && screenEl.value.querySelector('img')
  if (!img) return
  const r = img.getBoundingClientRect()
  const x = (ev.clientX - r.left) / r.width
  const y = (ev.clientY - r.top) / r.height
  if (x < 0 || x > 1 || y < 0 || y > 1) return
  if (sock) sock.send({ type: 'tap', deviceId: props.device.id, x, y })
  setTimeout(reqSnapshot, 400)
}

async function kick() {
  try {
    await kickDevice(props.device.id)
  } catch (e) {
    /* ignore */
  }
  emit('refresh')
}
</script>

<style scoped>
.remote { display: flex; flex-direction: column; height: 100%; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #111;
  border-radius: 6px;
  overflow: hidden;
}
.shot { max-width: 100%; max-height: 100%; object-fit: contain; cursor: crosshair; }
</style>
