<template>
  <div class="remote">
    <div class="toolbar">
      <el-tag :type="online ? 'success' : 'danger'">{{ online ? '在线' : '离线' }}</el-tag>

      <el-switch v-model="autoOn" size="small" active-text="自动刷新" @change="onAutoToggle" />

      <el-radio-group v-model="interval" size="small" :disabled="!autoOn" @change="onIntervalChange">
        <el-radio-button :value="3000">慢</el-radio-button>
        <el-radio-button :value="1500">标准</el-radio-button>
        <el-radio-button :value="800">快</el-radio-button>
      </el-radio-group>

      <span v-if="autoOn && refreshing" class="spinner"></span>
      <span v-else-if="autoOn && !paused && nextIn > 0" class="hint">下一帧 {{ nextIn }}s</span>
      <span v-if="autoOn && paused" class="hint paused">已暂停：{{ pausedReason }}</span>

      <el-button size="small" @click="snapshotNow">截屏</el-button>
      <el-button size="small" @click="key('back')">返回</el-button>
      <el-button size="small" @click="key('home')">主页</el-button>
      <el-button size="small" @click="key('vol_up')">音量 +</el-button>
      <el-button size="small" @click="key('vol_down')">音量 -</el-button>
      <el-button size="small" type="danger" plain @click="kick">断开</el-button>
    </div>

    <div ref="screenEl" class="screen" @click="onClick">
      <img v-if="imgUrl" :src="imgUrl" class="shot" />
      <el-empty v-else description="点击「截屏」查看画面" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { RemoteSocket } from '../ws'
import { kickDevice } from '../api'

const props = defineProps({ device: { type: Object, required: true } })
const emit = defineEmits(['refresh'])

const online = ref(props.device.online === 1 || props.device.online === true)
const imgUrl = ref('')
const screenEl = ref(null)

const autoOn = ref(false)
const interval = ref(1500)
const refreshing = ref(false)
const nextIn = ref(0)
const paused = ref(false)
const pausedReason = ref('')

let sock = null
let refreshActive = false
let loopBusy = false
let refreshNow = false
let refreshTimer = null
let countdownTimer = null
let pendingResolve = null
let timeoutStreak = 0

// ---------- 消息处理 ----------
function handle(msg) {
  if (msg.kind === 'binary') {
    const buf = msg.data
    if (buf.byteLength > 1 && new Uint8Array(buf)[0] === 0x01) {
      const blob = new Blob([buf.slice(1)], { type: 'image/jpeg' })
      if (imgUrl.value) URL.revokeObjectURL(imgUrl.value)
      imgUrl.value = URL.createObjectURL(blob)
    }
    if (pendingResolve) {
      const r = pendingResolve
      pendingResolve = null
      r({ ok: true, sent: true })
    }
    return
  }
  const d = msg.data
  if (d.type === 'device_status') {
    online.value = !!d.online
    if (d.online) resumeIfPaused()
    else pause('设备离线')
  } else if (d.type === 'session_state') {
    online.value = d.state === 'active'
    if (!online.value) pause('设备离线')
    else resumeIfPaused()
  }
}

function onStateChange(s) {
  if (!s.connected) stopLoop()
}

// ---------- 生命周期 ----------
onMounted(() => {
  sock = new RemoteSocket(handle, onStateChange)
  sock.deviceId = props.device.id
  sock.connect()
})

onBeforeUnmount(() => {
  stopLoop()
  if (imgUrl.value) URL.revokeObjectURL(imgUrl.value)
  if (sock) sock.close()
})

// ---------- 自动刷新 ----------
function onAutoToggle(v) {
  if (v) {
    paused.value = false
    startLoop()
  } else {
    stopLoop()
  }
}

function onIntervalChange() {
  refreshNow = true
  if (!loopBusy) scheduleNext(0)
}

function startLoop() {
  if (refreshActive) return
  refreshActive = true
  refreshLoop()
}

function stopLoop() {
  refreshActive = false
  clearTimeout(refreshTimer)
  clearInterval(countdownTimer)
  nextIn.value = 0
  refreshing.value = false
  if (pendingResolve) {
    const r = pendingResolve
    pendingResolve = null
    r({ ok: false, sent: false })
  }
}

function pause(reason) {
  paused.value = true
  pausedReason.value = reason
  stopLoop()
}

function resumeIfPaused() {
  if (autoOn.value && paused.value) {
    paused.value = false
    startLoop()
  }
}

function scheduleNext(delay) {
  clearTimeout(refreshTimer)
  clearInterval(countdownTimer)
  if (!refreshActive) return
  nextIn.value = Math.ceil(delay / 1000)
  countdownTimer = setInterval(() => {
    if (nextIn.value > 0) nextIn.value -= 1
  }, 1000)
  refreshTimer = setTimeout(refreshLoop, delay)
}

async function refreshLoop() {
  if (!refreshActive || loopBusy) return
  loopBusy = true
  refreshing.value = true
  const res = await requestSnapshot()
  refreshing.value = false
  loopBusy = false
  if (!refreshActive) return
  if (res.ok) {
    timeoutStreak = 0
    paused.value = false
    const d = refreshNow ? 0 : interval.value
    refreshNow = false
    scheduleNext(d)
  } else if (!res.sent) {
    pause('设备离线')
  } else {
    timeoutStreak += 1
    if (timeoutStreak >= 3) {
      pause('连续超时')
      ElMessage.warning('连续超时，已暂停自动刷新')
      return
    }
    scheduleNext(500)
  }
}

function requestSnapshot(timeoutMs = 6000) {
  return new Promise((resolve) => {
    if (!sock || !sock.isOpen()) {
      resolve({ ok: false, sent: false })
      return
    }
    pendingResolve = resolve
    sock.send({ type: 'snapshot_request', deviceId: props.device.id })
    setTimeout(() => {
      if (pendingResolve === resolve) {
        pendingResolve = null
        resolve({ ok: false, sent: true })
      }
    }, timeoutMs)
  })
}

// 手动截屏 / 操作后补帧：自动刷新开着就由循环立即补一帧（保持串行），否则单次请求
function snapshotNow() {
  refreshNow = true
  if (!autoOn.value) {
    requestSnapshot()
    return
  }
  if (!refreshActive) {
    paused.value = false
    startLoop()
    return
  }
  if (!loopBusy) {
    clearTimeout(refreshTimer)
    clearInterval(countdownTimer)
    refreshLoop()
  }
}

// ---------- 遥控操作 ----------
function key(k) {
  if (sock) sock.send({ type: 'system_key', deviceId: props.device.id, key: k })
  snapshotNow()
}

function onClick(ev) {
  const img = screenEl.value && screenEl.value.querySelector('img')
  if (!img) return
  const r = img.getBoundingClientRect()
  const x = (ev.clientX - r.left) / r.width
  const y = (ev.clientY - r.top) / r.height
  if (x < 0 || x > 1 || y < 0 || y > 1) return
  if (sock) sock.send({ type: 'tap', deviceId: props.device.id, x, y })
  snapshotNow()
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
.hint { font-size: 12px; color: #909399; }
.hint.paused { color: #e6a23c; }
.spinner {
  width: 14px; height: 14px; display: inline-block;
  border: 2px solid #dcdfe6; border-top-color: #409eff; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
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
