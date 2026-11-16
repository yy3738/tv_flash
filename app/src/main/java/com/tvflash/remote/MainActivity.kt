package com.tvflash.remote

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView

class MainActivity : Activity() {

    private lateinit var tvStatus: TextView
    private lateinit var tvPairCode: TextView
    private lateinit var ivPreview: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        tvPairCode = findViewById(R.id.tvPairCode)
        ivPreview = findViewById(R.id.ivPreview)

        tvPairCode.text = "配对码：" + (100000..999999).random()

        findViewById<Button>(R.id.btnCapture).setOnClickListener {
            if (!ScreenCaptureService.isReady()) {
                tvStatus.text = "无障碍状态：未开启，请先开启"
                return@setOnClickListener
            }
            ScreenCaptureService.instance?.captureScreen { bmp ->
                runOnUiThread {
                    if (bmp != null) {
                        ivPreview.setImageBitmap(bmp)
                        tvStatus.text = "截图成功 ${bmp.width}x${bmp.height}"
                    } else {
                        tvStatus.text = "截图失败（需 Android 11 / API 30+）"
                    }
                }
            }
        }

        findViewById<Button>(R.id.btnTap).setOnClickListener {
            val svc = ScreenCaptureService.instance
            if (svc == null) {
                tvStatus.text = "无障碍状态：未开启，无法注入"
                return@setOnClickListener
            }
            val dm = resources.displayMetrics
            val ok = svc.tap(dm.widthPixels / 2f, dm.heightPixels / 2f)
            tvStatus.text = if (ok) "已发送点击（屏幕中心）" else "点击注入失败"
        }
    }

    override fun onResume() {
        super.onResume()
        tvStatus.text = if (ScreenCaptureService.isReady())
            "无障碍状态：已开启"
        else
            "无障碍状态：未开启（去 设置 → 无障碍 开启 TV Flash）"
    }
}
