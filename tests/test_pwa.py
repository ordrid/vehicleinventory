"""What the Android app (a Trusted Web Activity built with Bubblewrap) reads from the site.

Bubblewrap builds the APK from the web manifest, and Android only opens the
site full-screen, without Chrome's address bar, if
/.well-known/assetlinks.json names the app's package and signing key. Both
values exist only once `bubblewrap init` has made the key, so they come from
the environment rather than the code.
"""

from __future__ import annotations

import json

from rental import create_app
from tests.conftest import TEST_CONFIG

FINGERPRINT = ":".join(["AB"] * 32)


def test_every_page_links_the_manifest(client):
    page = client.get("/login").get_data(as_text=True)
    assert 'rel="manifest" href="/static/manifest.webmanifest"' in page


def test_the_manifest_is_installable(client):
    """Bubblewrap refuses a manifest without a name, a start URL and a 512px icon."""
    response = client.get("/static/manifest.webmanifest")
    assert response.status_code == 200
    manifest = json.loads(response.get_data(as_text=True))
    assert manifest["name"] and manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    for icon in manifest["icons"]:
        assert client.get(icon["src"]).status_code == 200
    assert {icon["sizes"] for icon in manifest["icons"]} >= {"192x192", "512x512"}


def test_asset_links_is_empty_until_the_app_is_configured(client):
    """An empty list is valid JSON that claims no app, rather than a 404."""
    response = client.get("/.well-known/assetlinks.json")
    assert response.status_code == 200
    assert response.json == []


def test_asset_links_names_the_configured_app():
    app = create_app(
        TEST_CONFIG
        | {
            "ANDROID_PACKAGE_NAME": "com.example.rental",
            # Play App Signing adds a second key, so a list is accepted.
            "ANDROID_CERT_FINGERPRINTS": f"{FINGERPRINT}, {FINGERPRINT.replace('AB', 'CD')}",
        }
    )
    response = app.test_client().get("/.well-known/assetlinks.json")

    assert response.mimetype == "application/json"
    assert response.json == [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.example.rental",
                "sha256_cert_fingerprints": [FINGERPRINT, FINGERPRINT.replace("AB", "CD")],
            },
        }
    ]
