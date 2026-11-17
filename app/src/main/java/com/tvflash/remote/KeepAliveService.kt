package com.tvflash.remote

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder

class KeepAliveService : Service() {

    private var client: TvClient? = null

    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIF_ID, buildNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        connectFromPrefs()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        client?.close()
        super.onDestroy()
    }

    private fun connectFromPrefs() {
        val prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
        val url = prefs.getString("url", "").orEmpty()
        val token = prefs.getString("token", "").orEmpty()
        if (url.isEmpty() || token.isEmpty()) {
            ConnectionState.text = "未配置 NAS 地址或令牌"
            return
        }
        client?.close()
        client = TvClient(url, token) { state -> ConnectionState.text = state }
        client?.connect()
    }

    private fun buildNotification(): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL_ID, "TV Flash", NotificationManager.IMPORTANCE_LOW)
                )
            }
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("TV Flash 运行中")
            .setContentText("等待远程连接")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val ACTION_RECONNECT = "com.tvflash.remote.RECONNECT"
        private const val CHANNEL_ID = "tvflash_keepalive"
        private const val NOTIF_ID = 1001
    }
}
