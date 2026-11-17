// 浏览器 ↔ NAS 的实时通道封装
export class RemoteSocket {
  constructor(onMessage) {
    this.ws = null
    this.onMessage = onMessage
    this.deviceId = null
  }

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    this.ws = new WebSocket(`${proto}://${location.host}/ws/web`)
    this.ws.binaryType = 'arraybuffer'
    this.ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        this.onMessage({ kind: 'json', data: JSON.parse(ev.data) })
      } else {
        this.onMessage({ kind: 'binary', data: ev.data })
      }
    }
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve()
      this.ws.onerror = (e) => reject(e)
    })
  }

  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj))
    }
  }

  openSession(deviceId) {
    this.deviceId = deviceId
    this.send({ type: 'open_session', deviceId })
  }

  close() {
    if (this.ws) this.ws.close()
  }
}
