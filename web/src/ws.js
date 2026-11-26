// 浏览器 ↔ NAS 的实时通道封装（含断线重连）
export class RemoteSocket {
  constructor(onMessage, onStateChange) {
    this.ws = null
    this.onMessage = onMessage
    this.onStateChange = onStateChange || (() => {})
    this.deviceId = null
    this.manualClose = false
    this.retryDelay = 1000
    this.retryTimer = null
  }

  connect() {
    this.manualClose = false
    this._open()
  }

  _open() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/web`)
    this.ws = ws
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => {
      this.retryDelay = 1000
      this.onStateChange({ connected: true })
      // 重连成功后自动恢复会话
      if (this.deviceId) this.send({ type: 'open_session', deviceId: this.deviceId })
    }
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        this.onMessage({ kind: 'json', data: JSON.parse(ev.data) })
      } else {
        this.onMessage({ kind: 'binary', data: ev.data })
      }
    }
    ws.onclose = () => {
      this.onStateChange({ connected: false })
      if (this.manualClose) return
      this.retryTimer = setTimeout(() => this._open(), this.retryDelay)
      this.retryDelay = Math.min(this.retryDelay * 2, 10000)
    }
    ws.onerror = () => {
      // onclose 会跟着触发，重连逻辑在 onclose
    }
  }

  isOpen() {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  send(obj) {
    if (this.isOpen()) this.ws.send(JSON.stringify(obj))
  }

  openSession(deviceId) {
    this.deviceId = deviceId
    this.send({ type: 'open_session', deviceId })
  }

  close() {
    this.manualClose = true
    clearTimeout(this.retryTimer)
    if (this.ws) this.ws.close()
  }
}
