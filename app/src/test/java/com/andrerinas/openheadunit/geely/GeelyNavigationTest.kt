package com.andrerinas.openheadunit.geely

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Looper
import com.andrerinas.openheadunit.aap.AapNavigationHelper
import com.andrerinas.openheadunit.contract.NavigationUpdateIntent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class, sdk = [28])
class GeelyNavigationTest {
    @Test fun `a local widget without a signature permission receives navigation updates`() {
        val context = RuntimeEnvironment.getApplication()
        var received: Intent? = null
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) { received = intent }
        }
        context.registerReceiver(receiver, IntentFilter(NavigationUpdateIntent.action))
        try {
            AapNavigationHelper(context).sendFullNavigationBroadcast(
                AapNavigationHelper.NavigationSnapshot(), 0
            )
            shadowOf(Looper.getMainLooper()).idle()
            assertNotNull(received)
            assertEquals(NavigationUpdateIntent.action, received!!.action)
        } finally {
            context.unregisterReceiver(receiver)
        }
    }
}
