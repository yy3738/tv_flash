package com.tvflash.remote

import android.graphics.Bitmap
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

/** 电视端连接 NAS 的 WebSocket 客户端：接收指令、回传快照，断线自动重连。 */
class TvClient(
    private val baseUrl: String,
    private val token: String,
    private val onState: (String) -> Unit,
) {
    private val http = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()
    private val handler = Handler(Looper.getMainLooper())
    private var ws: WebSocket? = null
    private var manualClose = false
    private var lastSnapshotRequestAt = 0L

    private val reconnect = Runnable { connectInternal() }

    fun connect() {
        manualClose = false
        handler.removeCallbacks(reconnect)
        connectInternal()
    }

    private fun connectInternal() {
        if (manualClose) return
        val wsUrl = baseUrl.trim().trimEnd('/')
            .replaceFirst("https://", "wss://")
            .replaceFirst("http://", "ws://") + "/ws/tv?token=" + token
        val request = Request.Builder().url(wsUrl).build()
        ws = http.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onState("已连接 NAS")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleCommand(text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                // 电视端不接收二进制
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onState("断开，${RECONNECT_DELAY_MS / 1000}s 后重连")
                scheduleReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onState("已断开，${RECONNECT_DELAY_MS / 1000}s 后重连")
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        if (manualClose) return
        handler.removeCallbacks(reconnect)
        handler.postDelayed(reconnect, RECONNECT_DELAY_MS)
    }

    private fun handleCommand(text: String) {
        val obj = try {
            JSONObject(text)
        } catch (e: Exception) {
            return
        }
        when (obj.optString("type")) {
            "snapshot_request" -> sendSnapshot()
            "tap" -> {
                val x = obj.optDouble("x", -1.0).toFloat()
                val y = obj.optDouble("y", -1.0).toFloat()
                if (x >= 0f && y >= 0f) ScreenCaptureService.instance?.tapNormalized(x, y)
            }
            "swipe" -> {
                val x1 = obj.optDouble("x1", 0.0).toFloat()
                val y1 = obj.optDouble("y1", 0.0).toFloat()
                val x2 = obj.optDouble("x2", 0.0).toFloat()
                val y2 = obj.optDouble("y2", 0.0).toFloat()
                val d = obj.optLong("durationMs", 200L)
                ScreenCaptureService.instance?.swipeNormalized(x1, y1, x2, y2, d)
            }
            "system_key" -> ScreenCaptureService.instance?.systemKey(obj.optString("key"))
            else -> Unit
        }
    }

    private fun sendSnapshot() {
        val now = SystemClock.elapsedRealtime()
        if (now - lastSnapshotRequestAt < SNAPSHOT_MIN_INTERVAL_MS) return
        lastSnapshotRequestAt = now
        val service = ScreenCaptureService.instance ?: return
        service.captureScreen { bmp ->
            if (bmp == null) return@captureScreen
            val scaled = if (bmp.width > MAX_IMAGE_WIDTH) {
                val h = bmp.height * MAX_IMAGE_WIDTH / bmp.width
                Bitmap.createScaledBitmap(bmp, MAX_IMAGE_WIDTH, h, true)
            } else {
                bmp
            }
            val out = ByteArrayOutputStream()
            scaled.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
            if (scaled !== bmp) scaled.recycle()
            val data = out.toByteArray()
            val payload = ByteArray(data.size + 1)
            payload[0] = 0x01
            System.arraycopy(data, 0, payload, 1, data.size)
            ws?.send(ByteString.of(*payload))
        }
    }

    fun close() {
        manualClose = true
        handler.removeCallbacks(reconnect)
        try {
            ws?.close(1000, null)
        } catch (e: Exception) {
            // ignore
        }
        ws = null
    }

    companion object {
        private const val RECONNECT_DELAY_MS = 3000L
        private const val SNAPSHOT_MIN_INTERVAL_MS = 500L
        private const val MAX_IMAGE_WIDTH = 1280
        private const val JPEG_QUALITY = 65
    }
}
