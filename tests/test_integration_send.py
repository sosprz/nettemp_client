import os
import sys
import json
from types import SimpleNamespace
from pathlib import Path


# Ensure client root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_insert2_sends_to_cloud(tmp_path, monkeypatch):
    # Prepare a minimal config.conf in the client directory
    client_dir = Path(__file__).resolve().parents[1]
    config_file = client_dir / 'config.conf'

    config = {
        'group': 'testgroup',
        'cloud_servers': [
            {
                'url': 'http://example.com',
                'api_key': 'apikey',
                'enabled': True,
                'verify_ssl': False,
                'format': 'cloud'
            }
        ]
    }

    # Write config to client/config.conf (will overwrite if exists — restore later)
    orig = None
    if config_file.exists():
        orig = config_file.read_text()
    try:
        # Write a minimal YAML string so file exists; we inject a fake yaml loader below
        yaml_text = (
            "group: testgroup\n"
            "cloud_servers:\n"
            "  - url: http://example.com\n"
            "    api_key: apikey\n"
            "    enabled: true\n"
            "    verify_ssl: false\n"
            "    format: cloud\n"
        )
        config_file.write_text(yaml_text)

        # Mock requests.post to capture calls
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None, verify=None):
            calls.append({'url': url, 'json': json, 'headers': headers, 'verify': verify})
            return SimpleNamespace(status_code=200)

        # Ensure a requests module exists (may not be installed in test env)
        fake_requests = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(sys.modules, 'requests', fake_requests)

        # Avoid requiring PyYAML in the test env by inserting a fake yaml module
        import types
        fake_yaml = types.SimpleNamespace(safe_load=lambda f: config)
        monkeypatch.setitem(sys.modules, 'yaml', fake_yaml)

        # Provide fake urllib3 (may not be installed in test env)
        fake_urllib3 = SimpleNamespace(disable_warnings=lambda *a, **k: None,
                           exceptions=SimpleNamespace(InsecureRequestWarning=Exception))
        monkeypatch.setitem(sys.modules, 'urllib3', fake_urllib3)

        # Call insert2.request() with sample data
        from nettemp import insert2

        sample = [{'rom': '_sensor1', 'type': 'temp', 'value': '21.5', 'name': 't1', 'unit': 'C'}]
        sender = insert2(sample)
        sender.request()

        # Assert our fake_post was called for cloud endpoint
        assert any('/api/v1/data' in c['url'] for c in calls)
        # Validate payload structure
        cloud_call = [c for c in calls if '/api/v1/data' in c['url']][0]
        payload = cloud_call['json']
        assert payload.get('device_id') == 'testgroup'
        assert isinstance(payload.get('readings'), list)
        assert len(payload['readings']) == 1

    finally:
        # Restore original config if present
        if orig is not None:
            config_file.write_text(orig)
        else:
            try:
                config_file.unlink()
            except Exception:
                pass