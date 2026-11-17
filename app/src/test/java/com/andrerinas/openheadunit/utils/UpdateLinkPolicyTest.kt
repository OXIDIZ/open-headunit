package com.andrerinas.openheadunit.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test

class UpdateLinkPolicyTest {

    private val base = "https://github.com/andreknieriem/open-headunit/releases"
    private val page = "$base/tag/v.3.5.0-beta3"
    private val apk = "$base/download/v.3.5.0-beta3/com.andrerinas.headunitrevived_3.5.0-beta3.apk"
    private val debugApk = "$base/download/v.3.5.0-beta3/com.andrerinas.headunitrevived_3.5.0-beta3_debug.apk"

    @Test
    fun picksTheReleaseApkAndSkipsTheDebugBuild() {
        val assets = listOf(
            "com.andrerinas.headunitrevived_3.5.0-beta3_debug.apk" to debugApk,
            "com.andrerinas.headunitrevived_3.5.0-beta3.apk" to apk,
        )
        assertEquals(apk, UpdateLinkPolicy.pickApk(assets))
    }

    @Test
    fun noReleaseApkGivesNull() {
        assertNull(UpdateLinkPolicy.pickApk(emptyList()))
        assertNull(UpdateLinkPolicy.pickApk(listOf("notes.txt" to "$base/notes.txt")))
        assertNull(UpdateLinkPolicy.pickApk(listOf("x_debug.apk" to debugApk)))
    }

    @Test
    fun apkIsPrimaryAndReleasePageIsSecondary() {
        assertEquals(
            UpdateLinkPolicy.Choice.APK to UpdateLinkPolicy.Choice.RELEASE_PAGE,
            UpdateLinkPolicy.choices(apk)
        )
    }

    @Test
    fun noApkLeavesOnlyTheReleasePage() {
        assertEquals(UpdateLinkPolicy.Choice.RELEASE_PAGE to null, UpdateLinkPolicy.choices(null))
    }

    private fun release(tag: String, vararg assets: String) = UpdateLinkPolicy.Release(
        tag, "$base/tag/$tag", assets.map { it to "$base/download/$tag/$it" }
    )

    @Test
    fun newestReleaseWithAnApkIsOffered() {
        val got = UpdateLinkPolicy.newestInstallable(listOf(
            release("v.3.5.0", "com.andrerinas.headunitrevived_3.5.0.apk"),
            release("v.4.0.0-alpha", "com.andrerinas.headunitrevived_4.0.0-alpha.apk"),
        ))!!
        assertEquals("4.0.0-alpha", got.tag)
        assertEquals("$base/tag/v.4.0.0-alpha", got.pageUrl)
        assertEquals("$base/download/v.4.0.0-alpha/com.andrerinas.headunitrevived_4.0.0-alpha.apk", got.apkUrl)
    }

    @Test
    fun releaseStillUploadingItsApkIsSkippedForTheNewestInstallable() {
        val got = UpdateLinkPolicy.newestInstallable(listOf(
            release("v.4.0.1"),
            release("v.4.0.0", "com.andrerinas.headunitrevived_4.0.0.apk"),
        ))!!
        assertEquals("4.0.0", got.tag)
    }

    @Test
    fun debugApkAloneDoesNotMakeAReleaseInstallable() {
        val got = UpdateLinkPolicy.newestInstallable(listOf(
            release("v.4.0.1", "com.andrerinas.headunitrevived_4.0.1_debug.apk"),
            release("v.4.0.0", "com.andrerinas.headunitrevived_4.0.0.apk"),
        ))!!
        assertEquals("4.0.0", got.tag)
    }

    @Test
    fun noInstallableReleaseGivesNull() {
        assertNull(UpdateLinkPolicy.newestInstallable(listOf(release("v.4.0.1"), release("2.1.0-artefacts"))))
        assertNull(UpdateLinkPolicy.newestInstallable(listOf(release("nightly", "app.apk"))))
    }
    @Test
    fun sameOhuVersionOffersANewCommitOnlyOnce() {
        val commit = "b".repeat(40)
        val next = UpdateLinkPolicy.newestInstallable(listOf(UpdateLinkPolicy.Release(
            "v.4.0.0-geely.${commit.take(12)}", page, listOf("app.apk" to apk), commit
        )))!!
        assertTrue(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), "a".repeat(12)))
        assertFalse(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), commit.take(12)))
        assertFalse(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), commit.take(12) + "-dirty"))
    }

    @Test
    fun oldFourPartReleaseCannotReplaceCurrentOhuBuild() {
        val commit = "b".repeat(40)
        val next = UpdateLinkPolicy.newestInstallable(listOf(
            UpdateLinkPolicy.Release("v.4.0.0-geely.new", page, listOf("new.apk" to apk), commit),
            UpdateLinkPolicy.Release("v.4.0.0.1", page, listOf("old.apk" to debugApk), "a".repeat(40))
        ))!!
        assertEquals(commit, next.sourceCommit)
        assertEquals(apk, next.apkUrl)
        assertFalse(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), commit.take(12)))
    }

    @Test
    fun missingOrBranchCommitDoesNotCauseEndlessSameVersionUpdates() {
        for (commit in listOf(null, "main", "unknown", "a".repeat(12))) {
            val next = UpdateLinkPolicy.newestInstallable(listOf(UpdateLinkPolicy.Release(
                "v.4.0.0-geely.new", page, listOf("app.apk" to apk), commit
            )))!!
            assertFalse(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), "b".repeat(12)))
        }
    }

    @Test
    fun newerOhuVersionWinsAndAnOlderVersionCannotBeOfferedByCommitDifference() {
        val next = UpdateLinkPolicy.newestInstallable(listOf(UpdateLinkPolicy.Release(
            "v.4.1.0-geely.new", page, listOf("app.apk" to apk), "b".repeat(40)
        )))!!
        assertTrue(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.0.0"), "unknown"))
        assertFalse(UpdateLinkPolicy.isUpdateAvailable(next, AppVersion.parse("4.2.0"), "a".repeat(12)))
    }

    @Test
    fun historicalForkReleaseAloneIsNotOfferedBackToTheCurrentApp() {
        val old = UpdateLinkPolicy.Release(
            "v.4.0.0.1", page, listOf("old.apk" to apk), "a".repeat(40)
        )
        assertNull(UpdateLinkPolicy.newestInstallable(listOf(old)))
    }

}
