package com.andrerinas.openheadunit.connection.carkey

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.view.KeyEvent
import androidx.core.content.ContextCompat
import androidx.core.content.IntentCompat
import com.andrerinas.openheadunit.App
import com.andrerinas.openheadunit.utils.AppLog

/**
 * GHUR-compatible ECARX steering-wheel and hardware-button receiver for this Geely fork.
 */
class CarKeyBroadcastReceiver : BroadcastReceiver(), CarKeyReceiver {

    companion object {
        val ACTIONS = arrayOf(
            "com.ecarx.media.action.KEY_EVENT",
            "com.ecarx.intent.action.MEDIA_BUTTON"
        )
    }

    private var context: Context? = null

    override val isSupported = true
    override val isSUNeeded = false

    override fun register(context: Context) {
        this.context = context

        val filter = IntentFilter().apply {
            priority = 1000
            ACTIONS.forEach { addAction(it) }
        }

        ContextCompat.registerReceiver(
            context,
            this,
            filter,
            ContextCompat.RECEIVER_EXPORTED
        )
    }

    override fun unregister() {
        this.context?.unregisterReceiver(this)
        this.context = null
    }

    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        AppLog.i("CarKeyReceiver: Handling intent action: $action")

        // Broadcast for KeymapFragment debugger (raw intent data)
        context.sendBroadcast(Intent("com.andrerinas.openheadunit.DEBUG_KEY").apply {
            setPackage(context.packageName)
            putExtra("action", action)
            intent.extras?.let { putExtras(it) }
        })

        // Try to abort broadcast to prevent other apps (like built-in radio) from reacting,
        // but ONLY while an active Android Auto projection session is ongoing.
        if (isOrderedBroadcast && App.provide(context).commManager.isConnected) {
            abortBroadcast()
        }

        // 1. Standard / OEM Media Button extraction (already has KeyEvent with proper DOWN/UP)
        if (action.endsWith("MEDIA_BUTTON") || action.endsWith("KEY_EVENT")) {
            val event = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_KEY_EVENT, KeyEvent::class.java)
            if (event != null) {
                if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) {
                    handleKey(context, event.keyCode, true)
                } else if (event.action == KeyEvent.ACTION_UP) {
                    handleKey(context, event.keyCode, false)
                }
            } else {
                val cmd = intent.getStringExtra("command") ?: intent.getStringExtra("cmd")
                val key = intent.getIntExtra("keycode", -1).takeIf { it > 0 }
                    ?: intent.getIntExtra("key_code", -1).takeIf { it > 0 }

                if (cmd != null) {
                    when (cmd.lowercase()) {
                        "next", "skip_next", "skip" -> handleClick(context, KeyEvent.KEYCODE_MEDIA_NEXT)
                        "previous", "skip_previous", "prev" -> handleClick(context, KeyEvent.KEYCODE_MEDIA_PREVIOUS)
                        "play", "start" -> handleClick(context, KeyEvent.KEYCODE_MEDIA_PLAY)
                        "pause" -> handleClick(context, KeyEvent.KEYCODE_MEDIA_PAUSE)
                        "togglepause", "playpause" -> handleClick(context, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE)
                    }
                } else if (key != null) {
                    handleClick(context, key)
                }
            }
            return
        }

    }
}
