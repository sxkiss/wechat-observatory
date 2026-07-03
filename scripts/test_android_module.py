#!/usr/bin/env python3
"""Unit tests for Android LSPosed module structure validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_android_module as module


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_project(root: Path) -> None:
    android_module = root / "android-module"
    main = android_module / "app" / "src" / "main"
    package_dir = main / "java" / "cc" / "wechat" / "observatory"

    write(
        android_module / "settings.gradle",
        '\n'.join(
            [
                'pluginManagement { repositories { google(); mavenCentral(); maven { url "https://api.xposed.info/" } } }',
                'dependencyResolutionManagement { repositories { google(); mavenCentral(); maven { url "https://api.xposed.info/" } } }',
                'include ":app"',
            ]
        ),
    )
    write(android_module / "build.gradle", 'plugins { id "com.android.application" version "8.7.0" apply false }')
    write(
        android_module / "app" / "build.gradle",
        '\n'.join(
            [
                'plugins { id "com.android.application" }',
                'android { namespace "cc.wechat.observatory"; compileSdk 35',
                'defaultConfig { applicationId "cc.wechat.observatory"; minSdk 23; targetSdk 35 } }',
                'dependencies { compileOnly "de.robv.android.xposed:api:82" }',
            ]
        ),
    )
    write(
        main / "AndroidManifest.xml",
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.INTERNET" />
  <application>
    <meta-data android:name="xposedmodule" android:value="true" />
    <meta-data android:name="xposeddescription" android:value="Wechat Observatory" />
    <meta-data android:name="xposedminversion" android:value="93" />
    <meta-data android:name="xposedscope" android:resource="@array/xposed_scope" />
    <activity android:name=".SettingsActivity" android:exported="true" />
    <provider android:name=".BridgeConfigProvider" android:exported="true" />
    <receiver android:name=".BridgeConfigReceiver" android:exported="true" />
  </application>
</manifest>""",
    )
    write(main / "assets" / "xposed_init", "cc.wechat.observatory.HookEntry\n")
    write(
        main / "res" / "values" / "arrays.xml",
        """<resources>
  <string-array name="xposed_scope">
    <item>com.tencent.mm</item>
  </string-array>
</resources>""",
    )
    write(
        package_dir / "HookEntry.java",
        """package cc.wechat.observatory;
class HookEntry implements IXposedHookLoadPackage {
  public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) {
    String packageName = "com.tencent.mm";
  }
}""",
    )
    write(package_dir / "BridgeConfigProvider.java")
    write(package_dir / "BridgeConfigReceiver.java")
    write(package_dir / "gateway" / "WebSocketFrame.java")
    write(package_dir / "wechat" / "SendResult.java")


def error_types(report: dict[str, object]) -> set[str]:
    return {str(item.get("type")) for item in report.get("errors", []) if isinstance(item, dict)}


def failed_checks(report: dict[str, object]) -> set[str]:
    return {str(item.get("check")) for item in report.get("errors", []) if isinstance(item, dict)}


class AndroidModuleValidatorTests(unittest.TestCase):
    def test_complete_module_structure_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)

            report = module.collect_report(root)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["package"], "cc.wechat.observatory")
        self.assertEqual(report["wechat_package"], "com.tencent.mm")
        self.assertEqual(report["errors"], [])

    def test_missing_required_file_fails_before_deep_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            (root / "android-module" / "app" / "src" / "main" / "assets" / "xposed_init").unlink()

            report = module.collect_report(root)

        self.assertFalse(report["ok"], report)
        self.assertIn("missing_file", error_types(report))
        self.assertNotIn("gradle", report)

    def test_xposed_scope_must_only_target_wechat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            write(
                root / "android-module" / "app" / "src" / "main" / "res" / "values" / "arrays.xml",
                """<resources>
  <string-array name="xposed_scope">
    <item>com.tencent.mm</item>
    <item>com.tencent.mobileqq</item>
  </string-array>
</resources>""",
            )

            report = module.collect_report(root)

        self.assertFalse(report["ok"], report)
        self.assertIn("xposed_entry_check_failed", error_types(report))
        self.assertIn("scope_only_wechat", failed_checks(report))

    def test_manifest_components_must_be_exported_for_configuration_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            manifest = root / "android-module" / "app" / "src" / "main" / "AndroidManifest.xml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    '<provider android:name=".BridgeConfigProvider" android:exported="true" />',
                    '<provider android:name=".BridgeConfigProvider" android:exported="false" />',
                ),
                encoding="utf-8",
            )

            report = module.collect_report(root)

        self.assertFalse(report["ok"], report)
        self.assertIn("manifest_check_failed", error_types(report))
        self.assertIn("config_provider_exported", failed_checks(report))

    def test_gradle_identity_must_match_module_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            app_build = root / "android-module" / "app" / "build.gradle"
            app_build.write_text(
                app_build.read_text(encoding="utf-8").replace(
                    'applicationId "cc.wechat.observatory"',
                    'applicationId "cc.wechat.wrong"',
                ),
                encoding="utf-8",
            )

            report = module.collect_report(root)

        self.assertFalse(report["ok"], report)
        self.assertIn("gradle_check_failed", error_types(report))
        self.assertIn("application_id_matches", failed_checks(report))


if __name__ == "__main__":
    unittest.main()
