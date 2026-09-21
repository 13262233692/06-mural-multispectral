/**
 * 协作 WebSocket 客户端：接收其他用户的标注变更与光标位置。
 */
export class CollaborationClient {
  constructor(imagesetId, handlers = {}) {
    this.imagesetId = imagesetId
    this.handlers = handlers
    this.socket = null
    this.reconnectTimer = null
  }

  connect() {
    const token = encodeURIComponent(localStorage.getItem('token') || '')
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    this.socket = new WebSocket(
      `${protocol}://${window.location.host}/ws/imagesets/${this.imagesetId}?token=${token}`,
    )
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.handlers[message.type]?.(message)
    }
    this.socket.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 2000)
    }
  }

  send(message) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message))
    }
  }

  sendCursor(x, y) {
    this.send({ type: 'cursor', x, y })
  }

  close() {
    clearTimeout(this.reconnectTimer)
    this.socket?.close()
    this.socket = null
  }
}
