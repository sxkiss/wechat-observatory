#!/usr/bin/env python3
"""Validate the Android LSPosed module structure without building the APK."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID_MODULE = ROOT / "android-module"
APP = ANDROID_MODULE / "app"
MAIN = APP / "src" / "main"

PACKAGE_NAME = "cc.wechat.observatory"
WECHAT_PACKAGE = "com.tencent.mm"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


@dataclass(frozen=True)
class ModulePaths:
    root: Path
    android_module: Path
    app: Path
    main: Path


def module_paths(root: Path = ROOT) -> ModulePaths:
    android_module = root / "android-module"
    app = android_module / "app"
    main = app / "src" / "main"
    return ModulePaths(root=root, android_module=android_module, app=app, main=main)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def require_file(path: Path, errors: list[dict[str, str]], root: Path = ROOT) -> bool:
    if path.is_file():
        return True
    errors.append({"type": "missing_file", "path": relative_path(path, root)})
    return False


def parse_xml(path: Path, errors: list[dict[str, str]], root: Path = ROOT) -> ET.Element | None:
    try:
        return ET.fromstring(read_text(path))
    except ET.ParseError as exc:
        errors.append({"type": "invalid_xml", "path": relative_path(path, root), "error": str(exc)})
        return None


def attr(element: ET.Element, name: str) -> str:
    return element.attrib.get(ANDROID_NS + name, "")


def required_files(paths: ModulePaths) -> list[Path]:
    main = paths.main
    return [
        paths.android_module / "settings.gradle",
        paths.android_module / "build.gradle",
        paths.app / "build.gradle",
        main / "AndroidManifest.xml",
        main / "assets" / "xposed_init",
        main / "res" / "values" / "arrays.xml",
        main / "java" / "cc" / "wechat" / "observatory" / "HookEntry.java",
        main / "java" / "cc" / "wechat" / "observatory" / "BridgeConfigProvider.java",
        main / "java" / "cc" / "wechat" / "observatory" / "BridgeConfigReceiver.java",
        main / "java" / "cc" / "wechat" / "observatory" / "gateway" / "WebSocketFrame.java",
        main / "java" / "cc" / "wechat" / "observatory" / "wechat" / "SendResult.java",
    ]


def check_required_files(errors: list[dict[str, str]], paths: ModulePaths | None = None) -> None:
    paths = paths or module_paths()
    required = [
        *required_files(paths),
    ]
    for path in required:
        require_file(path, errors, paths.root)


def check_gradle(errors: list[dict[str, str]], paths: ModulePaths | None = None) -> dict[str, object]:
    paths = paths or module_paths()
    settings = read_text(paths.android_module / "settings.gradle")
    root_build = read_text(paths.android_module / "build.gradle")
    app_build = read_text(paths.app / "build.gradle")

    checks = {
        "includes_app": 'include ":app"' in settings or 'include(":app")' in settings,
        "has_google_repository": "google()" in settings,
        "has_maven_central_repository": "mavenCentral()" in settings,
        "has_xposed_repository": "https://api.xposed.info/" in settings,
        "uses_android_application_plugin": 'id "com.android.application"' in root_build
        and 'id "com.android.application"' in app_build,
        "namespace_matches": f'namespace "{PACKAGE_NAME}"' in app_build,
        "application_id_matches": f'applicationId "{PACKAGE_NAME}"' in app_build,
        "has_xposed_compile_only": 'compileOnly "de.robv.android.xposed:api:82"' in app_build,
    }

    numeric_expectations = {
        "compileSdk": 35,
        "minSdk": 23,
        "targetSdk": 35,
    }
    for name, minimum in numeric_expectations.items():
        match = re.search(rf"\b{name}\s+(\d+)", app_build)
        checks[f"{name}_ok"] = bool(match and int(match.group(1)) >= minimum)

    for name, ok in checks.items():
        if not ok:
            errors.append({"type": "gradle_check_failed", "check": name})
    return checks


def check_manifest(errors: list[dict[str, str]], paths: ModulePaths | None = None) -> dict[str, object]:
    paths = paths or module_paths()
    manifest_path = paths.main / "AndroidManifest.xml"
    manifest = parse_xml(manifest_path, errors, paths.root)
    if manifest is None:
        return {}

    permissions = {attr(node, "name") for node in manifest.findall("uses-permission")}
    application = manifest.find("application")
    if application is None:
        errors.append({"type": "manifest_missing_application"})
        return {"internet_permission": "android.permission.INTERNET" in permissions}

    metadata = {attr(node, "name"): attr(node, "value") or attr(node, "resource") for node in application.findall("meta-data")}
    activities = {attr(node, "name"): attr(node, "exported") for node in application.findall("activity")}
    providers = {attr(node, "name"): attr(node, "exported") for node in application.findall("provider")}
    receivers = {attr(node, "name"): attr(node, "exported") for node in application.findall("receiver")}

    checks = {
        "internet_permission": "android.permission.INTERNET" in permissions,
        "xposedmodule": metadata.get("xposedmodule") == "true",
        "xposeddescription": bool(metadata.get("xposeddescription")),
        "xposedminversion": int(metadata.get("xposedminversion", "0")) >= 93,
        "xposedscope": metadata.get("xposedscope") == "@array/xposed_scope",
        "settings_activity_exported": activities.get(".SettingsActivity") == "true",
        "config_provider_exported": providers.get(".BridgeConfigProvider") == "true",
        "config_receiver_exported": receivers.get(".BridgeConfigReceiver") == "true",
    }
    for name, ok in checks.items():
        if not ok:
            errors.append({"type": "manifest_check_failed", "check": name})
    return checks


def check_xposed_entry(errors: list[dict[str, str]], paths: ModulePaths | None = None) -> dict[str, object]:
    paths = paths or module_paths()
    xposed_init = read_text(paths.main / "assets" / "xposed_init").strip()
    arrays_root = parse_xml(paths.main / "res" / "values" / "arrays.xml", errors, paths.root)
    hook_source = read_text(paths.main / "java" / "cc" / "wechat" / "observatory" / "HookEntry.java")

    scope_items: list[str] = []
    if arrays_root is not None:
        scope = arrays_root.find("./string-array[@name='xposed_scope']")
        if scope is not None:
            scope_items = [(item.text or "").strip() for item in scope.findall("item")]

    checks = {
        "xposed_init_points_to_hook": xposed_init == f"{PACKAGE_NAME}.HookEntry",
        "scope_only_wechat": scope_items == [WECHAT_PACKAGE],
        "hook_implements_load_package": "implements IXposedHookLoadPackage" in hook_source,
        "hook_has_handle_load_package": "handleLoadPackage(XC_LoadPackage.LoadPackageParam" in hook_source,
        "hook_filters_wechat": WECHAT_PACKAGE in hook_source,
    }
    for name, ok in checks.items():
        if not ok:
            errors.append({"type": "xposed_entry_check_failed", "check": name})
    return {**checks, "scope_items": scope_items}


def collect_report(root: Path = ROOT) -> dict[str, object]:
    paths = module_paths(root)
    errors: list[dict[str, str]] = []
    check_required_files(errors, paths)
    if errors:
        return {"ok": False, "errors": errors}

    summary = {
        "gradle": check_gradle(errors, paths),
        "manifest": check_manifest(errors, paths),
        "xposed_entry": check_xposed_entry(errors, paths),
    }
    return {
        "ok": not errors,
        "package": PACKAGE_NAME,
        "wechat_package": WECHAT_PACKAGE,
        **summary,
        "errors": errors,
    }


def main() -> int:
    result = collect_report()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
