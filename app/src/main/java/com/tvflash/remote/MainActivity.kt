package com.tvflash.remote

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView

class MainActivity : Activity() {

    private lateinit var tvStatus: TextView
    private lateinit var etUrl: EditText
    private lateinit var etToken: EditText
    private lateinit var ivPreview: ImageView
    private val handler = Handler(Looper.getMainLooper())
    private val ticker = object : Runnable {
        override fun run() {
            refreshStatus()
            handler.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        etUrl = findViewById(R.id.etUrl)
        etToken = findViewById(R.id.etToken)
        ivPreview = findViewById(R.id.ivPreview)

        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        etUrl.setText(prefs.getString("url", "http://127.0.0.1:8080"))
        etToken.setText(prefs.getString("token", ""))

        findViewById<Button>(R.id.btnSave).setOnClickListener {
            val url = etUrl.text.toString().trim()
            val token = etToken.text.toString().trim()
            prefs.edit().putString("url", url).putString("token", token).apply()
            ConnectionState.text = "保存，正在连接…"
            startKeepAlive()
        }

        findViewById<Button>(R.id.btnSnap).setOnClickListener { localSnapshot() }
    }

    override fun onResume() {
        super.onResume()
        handler.post(ticker)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(ticker)
    }

    private fun refreshStatus() {
        val acc = if (ScreenCaptureService.isReady()) "已开启" else "未开启"
        tvStatus.text = "无障碍:$acc | " + ConnectionState.text
    }

    private fun startKeepAlive() {
        val intent = Intent(this, KeepAliveService::class.java)
            .setAction(KeepAliveService.ACTION_RECONNECT)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun localSnapshot() {
        if (!ScreenCaptureService.isReady()) {
            tvStatus.text = "无障碍未开启"
            return
        }
        ScreenCaptureService.instance?.captureScreen { bmp ->
            runOnUiThread {
                if (bmp != null) {
                    ivPreview.setImageBitmap(bmp)
                    tvStatus.text = "截图 ${bmp.width}x${bmp.height}"
                } else {
                    tvStatus.text = "截图失败"
                }
            }
        }
    }

    companion object {
        const val PREFS = "tvflash"
    }
}
