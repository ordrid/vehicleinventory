"""The Digital Asset Links file that lets the Android app open this site full-screen.

The APK is a Trusted Web Activity built with Bubblewrap: a thin shell that
opens this site in Chrome. Android hides Chrome's address bar only when the
site vouches for the app here, by package name and signing-key fingerprint.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("android", __name__)


@bp.route("/.well-known/assetlinks.json")
def asset_links():
    """Name the app and the keys it is signed with, or nobody when unconfigured.

    ``ANDROID_CERT_FINGERPRINTS`` is comma-separated because Play App Signing
    re-signs uploads with Google's own key, and both keys must be listed.
    """
    package = current_app.config.get("ANDROID_PACKAGE_NAME", "")
    fingerprints = [
        fingerprint.strip()
        for fingerprint in current_app.config.get("ANDROID_CERT_FINGERPRINTS", "").split(",")
        if fingerprint.strip()
    ]
    if not package or not fingerprints:
        return jsonify([])
    return jsonify(
        [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    )
