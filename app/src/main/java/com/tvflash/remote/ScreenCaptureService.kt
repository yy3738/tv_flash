package com.tvflash.remote

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Bitmap
import android.graphics.Path
import android.media.AudioManager
import android.os.Build
import android.view.Display
import android.view.accessibility.AccessibilityEvent

class ScreenCaptureService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        if (instance === this) {
            instance = null
        }
    }

    fun captureScreen(callback: (Bitmap?) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            callback(null)
            return
        }
        takeScreenshot(
            Display.DEFAULT_DISPLAY,
            mainExecutor,
            object : AccessibilityService.TakeScreenshotCallback {
                override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                    val buffer = result.hardwareBuffer
                    val bitmap = Bitmap.wrapHardwareBuffer(buffer, result.colorSpace)
                        ?.copy(Bitmap.Config.ARGB_8888, false)
                    buffer.close()
                    callback(bitmap)
                }

                override fun onFailure(errorCode: Int) {
                    callback(null)
                }
            }
        )
    }

    fun tap(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val stroke = GestureDescription.StrokeDescription(path, 0L, 80L)
        return dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    fun swipe(x1: Float, y1: Float, x2: Float, y2: Float, durationMs: Long): Boolean {
        val path = Path().apply {
            moveTo(x1, y1)
            lineTo(x2, y2)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0L, durationMs)
        return dispatchGesture(GestureDescription.Builder().addStroke(stroke).build(), null, null)
    }

    fun tapNormalized(nx: Float, ny: Float): Boolean {
        val dm = resources.displayMetrics
        return tap(nx * dm.widthPixels, ny * dm.heightPixels)
    }

    fun swipeNormalized(nx1: Float, ny1: Float, nx2: Float, ny2: Float, durationMs: Long): Boolean {
        val dm = resources.displayMetrics
        return swipe(
            nx1 * dm.widthPixels, ny1 * dm.heightPixels,
            nx2 * dm.widthPixels, ny2 * dm.heightPixels, durationMs
        )
    }

    fun systemKey(key: String): Boolean {
        return when (key) {
            "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
            "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
            "vol_up" -> adjustVolume(AudioManager.ADJUST_RAISE)
            "vol_down" -> adjustVolume(AudioManager.ADJUST_LOWER)
            else -> false
        }
    }

    private fun adjustVolume(direction: Int): Boolean {
        val am = getSystemService(AudioManager::class.java) ?: return false
        am.adjustStreamVolume(AudioManager.STREAM_MUSIC, direction, AudioManager.FLAG_SHOW_UI)
        return true
    }

    companion object {
        @Volatile
        var instance: ScreenCaptureService? = null

        fun isReady(): Boolean = instance != null
    }
}
