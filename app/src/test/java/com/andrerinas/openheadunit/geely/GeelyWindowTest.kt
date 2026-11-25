package com.andrerinas.openheadunit.geely

import android.app.Activity
import android.app.Application
import android.content.Context
import android.view.ContextThemeWrapper
import android.view.LayoutInflater
import android.view.View
import com.andrerinas.openheadunit.R
import com.andrerinas.openheadunit.utils.Settings
import com.andrerinas.openheadunit.utils.SystemUI
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class, sdk = [28])
class GeelyWindowTest {
    private val context: Context get() = RuntimeEnvironment.getApplication()

    @Before fun resetPreferences() {
        context.getSharedPreferences(Settings.PREFS_NAME, Context.MODE_PRIVATE).edit().clear().commit()
    }

    @Test fun `fresh install reserves the climate dock and keeps system bars visible`() {
        val settings = Settings(context)
        assertEquals(Settings.FullscreenMode.NONE, settings.fullscreenMode)
        assertEquals(126, settings.insetBottom)
    }

    @Test fun `built in loading artwork has a visible text switch with an off default`() {
        val settings = Settings(context)
        assertFalse(settings.loadingScreenShowText)
        val inflater = LayoutInflater.from(ContextThemeWrapper(context, R.style.AppTheme))
        val screen = inflater.inflate(R.layout.fragment_loading_screen, null)
        var ancestor: View? = screen.findViewById<View>(R.id.toggle_show_text)
        while (ancestor != null) {
            assertEquals(View.VISIBLE, ancestor.visibility)
            ancestor = ancestor.parent as? View
        }
        assertEquals(View.GONE, screen.findViewById<View>(R.id.toggle_container).visibility)
    }

    @Test fun `an upgrade preserves user screen settings`() {
        Settings(context).apply {
            fullscreenMode = Settings.FullscreenMode.IMMERSIVE_WITH_NOTCH
            insetBottom = 42
        }
        val afterRestart = Settings(context)
        assertEquals(Settings.FullscreenMode.IMMERSIVE_WITH_NOTCH, afterRestart.fullscreenMode)
        assertEquals(42, afterRestart.insetBottom)
    }

    @Test fun `returning from immersive mode clears every legacy UI flag`() {
        val activity = Robolectric.buildActivity(Activity::class.java).setup().get()
        try {
            SystemUI.applySystemBars(activity.window, Settings.FullscreenMode.IMMERSIVE)
            @Suppress("DEPRECATION")
            assertTrue(activity.window.decorView.systemUiVisibility != 0)
            SystemUI.applySystemBars(activity.window, Settings.FullscreenMode.NONE)
            @Suppress("DEPRECATION")
            assertEquals(0, activity.window.decorView.systemUiVisibility)
        } finally {
            activity.finish()
        }
    }
}
