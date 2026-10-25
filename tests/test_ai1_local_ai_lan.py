"""AI-1: chỉ dữ liệu DEMO, máy AI giả loopback; không gọi LAN/Tailscale thật."""
from __future__ import annotations

import json
import os
import socket
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock, patch

from test_modules import FeatureCase
from kho_tri_thuc.giao_dien.operations import Operations, SOURCE_DEFAULTS
from kho_tri_thuc.tri_thuc import ai_cuc_bo as ai


OPTIONS = [{"code": "DEMO_A", "name": "DEMO Alpha"}, {"code": "DEMO_B", "name": "DEMO Beta"}]
ANSWER = "MA=DEMO_B | LY_DO=Khớp tên DEMO Beta"


def config(url="http://127.0.0.1:1234/v1/chat/completions", **kwargs):
    return {"enabled": True, "url": url, "model": "demo-local", "timeout_seconds": 2, **kwargs}


@contextmanager
def fake_ai(*, model_entry=None, tags=None, tags_payload=None, redirects=None, completion=None):
    calls = []
    responses = {
        "/v1/models": {"data": [model_entry or {"id": "demo-local"}]},
        "/v1/chat/completions": completion or {"choices": [{"message": {"content": ANSWER}}]},
    }
    if tags is not None:
        responses["/api/tags"] = {"models": tags}
    if tags_payload is not None:
        responses["/api/tags"] = tags_payload

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.reply()

        def do_POST(self):
            self.reply()

        def reply(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            calls.append((self.command, self.path, json.loads(raw) if raw else None))
            if self.path in (redirects or {}):
                self.send_response(307)
                self.send_header("Location", redirects[self.path])
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if self.path not in responses:
                self.send_error(404)
                return
            body = json.dumps(responses[self.path], ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield config(f"http://127.0.0.1:{server.server_port}/v1/chat/completions"), calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class AddressTests(unittest.TestCase):
    def test_default_remains_disabled(self):
        self.assertFalse(ai.local_ai_settings({})["enabled"])

    def test_accepts_only_explicit_loopback_rfc1918_and_tailscale_ranges(self):
        hosts = ("127.0.0.1", "127.2.3.4", "192.168.2.3", "10.2.3.4", "172.16.0.1",
                 "172.31.255.254", "100.64.0.1", "100.127.255.254", "[::1]", "[fd7a:115c:a1e0::2]")
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("Không được tra DNS")) as dns:
            for host in hosts:
                with self.subTest(host=host):
                    result = ai.local_ai_settings({"local_ai": config(f"http://{host}:1234/v1/chat/completions")})
                    self.assertTrue(result["enabled"], result["error"])
            dns.assert_not_called()

    def test_rejects_domains_https_public_linklocal_and_malformed_urls_without_dns(self):
        urls = ("http://ai.example:1234/v1/chat/completions", "http://0.0.0.0:1234/v1/chat/completions",
                "https://127.0.0.1:1234/v1/chat/completions", "http://8.8.8.8:1234/v1/chat/completions",
                "http://100.63.255.255:1234/v1/chat/completions", "http://100.128.0.1:1234/v1/chat/completions",
                "http://172.32.0.1:1234/v1/chat/completions", "http://169.254.1.2:1234/v1/chat/completions",
                "http://[fe80::1]:1234/v1/chat/completions", "http://[2001:db8::1]:1234/v1/chat/completions",
                "http://[::ffff:8.8.8.8]:1234/v1/chat/completions", "http://[::ffff:127.0.0.1]:1234/v1/chat/completions",
                "http://2130706433:1234/v1/chat/completions",
                "http://127.0.0.1/v1/chat/completions", "http://127.0.0.1:0/v1/chat/completions",
                "http://127.0.0.1:65536/v1/chat/completions", "http://user@127.0.0.1:1234/v1/chat/completions",
                "http://127.0.0.1:1234/v1/chat/completions?proxy=1",
                "http://127.0.0.1:1234/v1/chat/completions#fragment",
                "http://[fd7a:115c:a1e0::1%25eth0]:1234/v1/chat/completions",
                "http://127.0.0.1:1234/\nv1/chat/completions", "http://[broken")
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("Không được tra DNS")) as dns:
            transport = Mock(return_value=ANSWER)
            for url in urls:
                with self.subTest(url=url):
                    result = ai.local_ai_settings({"local_ai": config(url)})
                    self.assertFalse(result["enabled"])
                    self.assertTrue(result["error"])
                    self.assertIsNone(ai.choose_counterparty(config(url), "DEMO Beta", "DEMO", OPTIONS, transport))
            dns.assert_not_called()
            transport.assert_not_called()

    def test_tailscale_route_uses_tailscale_source_for_ipv4_and_ipv6(self):
        for host, source in (("100.64.1.2", "100.100.1.1"), ("[fd7a:115c:a1e0::2]", "fd7a:115c:a1e0::1")):
            with self.subTest(host=host), patch.object(ai, "source_address", return_value=source) as route:
                transport = Mock(return_value=ANSWER)
                result = ai.choose_counterparty(config(f"http://{host}:1234/v1/chat/completions"),
                                                "DEMO Beta", "DEMO", OPTIONS, transport)
                self.assertEqual("DEMO_B", result["code"])
                route.assert_called_once_with(host.strip("[]"), 1234)
                transport.assert_called_once()

    def test_tailscale_rejects_ordinary_or_unavailable_route_before_http(self):
        settings = config("http://100.64.1.2:1234/v1/chat/completions")
        for source in ("192.168.1.2", "10.1.2.3", "127.0.0.1", "invalid", OSError("no route")):
            kwargs = {"side_effect": source} if isinstance(source, Exception) else {"return_value": source}
            with self.subTest(source=source), patch.object(ai, "source_address", **kwargs), \
                    patch.object(ai.urllib.request, "build_opener") as opener:
                with self.assertRaisesRegex(ValueError, "bật Tailscale"):
                    ai._ask(settings, "DEMO")
                opener.assert_not_called()

    def test_tailscale_socket_binds_verified_source_without_getaddrinfo(self):
        sock = Mock()
        with patch.object(socket, "socket", return_value=sock), \
                patch.object(socket, "getaddrinfo") as dns:
            connection = ai._IPConnection("100.64.1.2:1234", source="100.100.1.1", timeout=2)
            connection.connect()
            sock.bind.assert_called_once_with(("100.100.1.1", 0))
            sock.connect.assert_called_once_with(("100.64.1.2", 1234))
            dns.assert_not_called()
            connection.close()

    def test_source_address_only_queries_udp_route(self):
        with patch.object(socket, "socket") as factory:
            probe = factory.return_value.__enter__.return_value
            probe.getsockname.return_value = ("100.100.1.1", 123)
            self.assertEqual("100.100.1.1", ai.source_address("100.64.1.2", 1234))
            factory.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect.assert_called_once_with(("100.64.1.2", 1234))
            probe.send.assert_not_called()
            probe.sendto.assert_not_called()

    def test_cloud_names_and_remote_config_are_disabled_without_transport(self):
        for extra in ({"model": "demo-CLOUD:latest"}, {"remote_host": "DEMO"}, {"remote_model": "DEMO"}):
            with self.subTest(extra=extra):
                settings = config(**extra)
                normalized = ai.local_ai_settings({"local_ai": settings})
                self.assertFalse(normalized["enabled"])
                self.assertIn("chọn model", normalized["error"])
                transport = Mock(return_value=ANSWER)
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS, transport))
                transport.assert_not_called()


class FakeAIIntegrationTests(unittest.TestCase):
    def test_legacy_localhost_connects_to_loopback_without_dns(self):
        with fake_ai() as (settings, calls), \
                patch.object(socket, "getaddrinfo", side_effect=AssertionError("Không được tra DNS")) as dns:
            settings["url"] = settings["url"].replace("127.0.0.1", "localhost")
            normalized = ai.local_ai_settings({"local_ai": settings})
            self.assertTrue(normalized["enabled"])
            self.assertIn("127.0.0.1", normalized["url"])
            connect = ai._IPConnection.connect
            hosts = []

            def record_connect(connection):
                hosts.append(connection.host)
                return connect(connection)

            with patch.object(ai._IPConnection, "connect", record_connect):
                self.assertEqual("DEMO_B", ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS)["code"])
            self.assertEqual(["127.0.0.1"] * 3, hosts)
            self.assertEqual("/v1/chat/completions", calls[-1][1])
            dns.assert_not_called()

    def test_choose_counterparty_works_without_dns_or_environment_proxy(self):
        with fake_ai() as (settings, calls), patch.dict(os.environ, {
                "HTTP_PROXY": "http://proxy.invalid:9999", "http_proxy": "http://proxy.invalid:9999",
                "HTTPS_PROXY": "http://proxy.invalid:9999", "ALL_PROXY": "http://proxy.invalid:9999",
                "NO_PROXY": "", "no_proxy": ""}), \
                patch.object(socket, "getaddrinfo", side_effect=AssertionError("Không được tra DNS")) as dns:
            result = ai.choose_counterparty(settings, "DEMO Beta", "Chuyển tiền DEMO", OPTIONS)
            self.assertEqual({"code": "DEMO_B", "reason": "Khớp tên DEMO Beta"}, result)
            self.assertEqual([("GET", "/v1/models"), ("GET", "/api/tags"), ("POST", "/v1/chat/completions")],
                             [(method, path) for method, path, _ in calls])
            body = calls[-1][2]
            self.assertEqual("demo-local", body["model"])
            self.assertIn("DEMO Beta", body["messages"][1]["content"])
            dns.assert_not_called()

    def test_ollama_uses_openai_completion_with_local_metadata(self):
        with fake_ai(model_entry={"id": "demo-local:latest"},
                     tags=[{"name": "demo-local:latest", "model": "demo-local:latest"}]) as (settings, calls):
            self.assertEqual("DEMO_B", ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS)["code"])
            self.assertEqual("/v1/chat/completions", calls[-1][1])

    def test_lm_studio_unknown_tags_payload_does_not_block_completion(self):
        for payload in ({}, {"error": "Unexpected endpoint"}, {"models": None}, {"models": {}}, []):
            with self.subTest(payload=payload), fake_ai(tags_payload=payload) as (settings, calls):
                self.assertEqual("DEMO_B", ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS)["code"])
                self.assertEqual("/v1/chat/completions", calls[-1][1])

    def test_ollama_empty_or_nonmatching_models_list_still_blocks_prompt(self):
        for tags in ([], [{"name": "another-demo-model"}]):
            with self.subTest(tags=tags), fake_ai(tags=tags) as (settings, calls):
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS))
                self.assertTrue(all(method == "GET" for method, _, _ in calls))

    def test_remote_model_metadata_blocks_prompt_even_with_innocent_name(self):
        for metadata in ({"remote_host": "DEMO"}, {"remote_model": "DEMO"}, {"model": "demo-cloud"}):
            with self.subTest(metadata=metadata), fake_ai(model_entry={"id": "demo-local", **metadata}) as (settings, calls):
                with self.assertRaisesRegex(ValueError, "chọn model chạy trên máy AI"):
                    ai._ask(settings, "DEMO PRIVATE PROMPT")
                self.assertEqual([("GET", "/v1/models", None)], calls)

    def test_ollama_remote_tags_block_prompt_before_post(self):
        for metadata in ({"remote_host": "DEMO"}, {"remote_model": "DEMO"}, {"model": "demo-cloud"}):
            with self.subTest(metadata=metadata), \
                    fake_ai(tags=[{"name": "demo-local:latest", **metadata}]) as (settings, calls):
                with self.assertRaisesRegex(ValueError, "chọn model chạy trên máy AI"):
                    ai._ask(settings, "DEMO PRIVATE PROMPT")
                self.assertTrue(all(method == "GET" and body is None for method, _, body in calls))

    def test_missing_model_blocks_prompt(self):
        with fake_ai(model_entry={"id": "another-demo-model"}) as (settings, calls):
            with self.assertRaisesRegex(ValueError, "đặt đúng tên"):
                ai._ask(settings, "DEMO")
            self.assertTrue(all(method == "GET" for method, _, _ in calls))

    def test_redirects_are_never_followed_for_metadata_or_completion(self):
        for path in ("/v1/models", "/api/tags", "/v1/chat/completions"):
            with self.subTest(path=path), fake_ai(redirects={path: "/redirected"}) as (settings, calls):
                with self.assertRaisesRegex(ValueError, "(không chuyển hướng|kiểm tra dịch vụ Local AI)"):
                    ai._ask(settings, "DEMO")
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS))
                self.assertFalse(any(url == "/redirected" for _, url, _ in calls))

    def test_output_must_still_choose_an_offered_code(self):
        with fake_ai(completion={"choices": [{"message": {"content": "MA=DEMO_OTHER"}}]}) as (settings, _):
            self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS))


class ConnectionCooldownTests(unittest.TestCase):
    def setUp(self):
        self.cache = patch.dict(ai._CONNECTION_FAILURES, {}, clear=True)
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def test_connection_failures_skip_network_for_15_seconds_then_retry(self):
        errors = (ai.urllib.error.URLError(ConnectionRefusedError("DEMO offline")),
                  TimeoutError("DEMO timeout"), ai.http.client.RemoteDisconnected("DEMO closed"))
        for error in errors:
            with self.subTest(error=type(error).__name__), \
                    patch.dict(ai._CONNECTION_FAILURES, {}, clear=True), \
                    patch.object(ai.time, "monotonic", return_value=100) as clock, \
                    patch.object(ai.urllib.request, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                settings = config("http://localhost:1234/v1/chat/completions")
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO PRIVATE", "DEMO PROMPT", OPTIONS))
                self.assertEqual({config()["url"]: 100}, ai._CONNECTION_FAILURES)
                clock.return_value = 114.99
                self.assertIsNone(ai.choose_counterparty(config(), "DEMO", "DEMO", OPTIONS))
                factory.assert_called_once()
                factory.return_value.open.assert_called_once()
                transport = Mock(return_value=ANSWER)
                other = config("http://127.0.0.1:1235/v1/chat/completions")
                self.assertEqual("DEMO_B", ai.choose_counterparty(other, "DEMO", "DEMO", OPTIONS, transport)["code"])
                clock.return_value = 115
                self.assertEqual("DEMO_B", ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS, transport)["code"])
                self.assertEqual(2, transport.call_count)
                self.assertEqual({}, ai._CONNECTION_FAILURES)

    def test_completion_connection_failure_also_starts_cooldown(self):
        with fake_ai() as (settings, calls), patch.object(ai.time, "monotonic", return_value=100):
            # Mock metadata separately so the failed socket belongs to completion.
            read_json = ai._read_json

            def read(opener, url, timeout, body=None):
                if url.endswith("/v1/models"):
                    return {"data": [{"id": "demo-local"}]}
                if url.endswith("/api/tags"):
                    return {}
                return read_json(opener, url, timeout, body)

            with patch.object(ai, "_read_json", side_effect=read), \
                    patch.object(ai._IPConnection, "connect", side_effect=TimeoutError("DEMO timeout")) as connect:
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS))
                self.assertIsNone(ai.choose_counterparty(settings, "DEMO", "DEMO", OPTIONS))
                connect.assert_called_once()
                self.assertEqual({settings["url"]: 100}, ai._CONNECTION_FAILURES)
            self.assertEqual([], calls)

    def test_model_or_answer_error_does_not_start_connection_cooldown(self):
        transport = Mock(side_effect=[ValueError("DEMO model error"), ANSWER])
        self.assertIsNone(ai.choose_counterparty(config(), "DEMO", "DEMO", OPTIONS, transport))
        self.assertEqual("DEMO_B", ai.choose_counterparty(config(), "DEMO", "DEMO", OPTIONS, transport)["code"])
        self.assertEqual({}, ai._CONNECTION_FAILURES)


class LocalAISettingsTests(FeatureCase):
    def setUp(self):
        super().setUp()
        self.operation = object.__new__(Operations)
        self.operation.config = self.config
        self.operation.config_path = self.root / "cau_hinh-demo.toml"
        self.operation.root = self.root
        self.operation._mutation_lock = threading.RLock()
        self.operation.bootstrap_job = None
        self.operation.bootstrap_status = {}
        self.paths = {key: str(self.root / key) for key in SOURCE_DEFAULTS}

    def write_settings(self, local_ai):
        (self.root / "source-settings.json").write_text(
            json.dumps({"paths": self.paths, "settings": {"local_ai": local_ai}}, ensure_ascii=False), encoding="utf-8")

    def test_old_localhost_config_is_normalized_before_ui_reads_it(self):
        self.write_settings(config("http://localhost:1234/v1/chat/completions", timeout_seconds=99, error="Lỗi cũ"))
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("Không được tra DNS")) as dns:
            settings = self.operation.source_settings()["settings"]["local_ai"]
            self.assertTrue(settings["enabled"])
            self.assertEqual("", settings["error"])
            self.assertEqual(config()["url"], settings["url"])
            self.assertEqual(30, settings["timeout_seconds"])
            self.assertEqual(settings, self.operation.overview()["local_ai"])
            dns.assert_not_called()

    def test_invalid_config_shows_ui_error_but_saving_preserves_user_enabled(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                local_ai = config("http://0.0.0.0:1234/v1/chat/completions", enabled=enabled, error="Lỗi cũ")
                result = self.operation.save_source_settings({"paths": self.paths, "settings": {"local_ai": local_ai}})
                self.assertFalse(result["settings"]["local_ai"]["enabled"])
                self.assertTrue(self.operation.overview()["local_ai"]["error"])
                # Lưu mục khác và đồng bộ lúc khởi động cũng phải giữ enabled gốc.
                self.operation._sync_runtime_settings()
                self.operation.save_learning_settings({"scoring_mode": True})
                saved = json.loads((self.root / "source-settings.json").read_text(encoding="utf-8"))["settings"]["local_ai"]
                self.assertEqual(enabled, saved["enabled"])
                self.assertNotIn("error", saved)
                runtime = json.loads(self.store.conn.execute(
                    "SELECT value FROM workspace_meta WHERE key='v9b_runtime_settings'").fetchone()[0])["local_ai"]
                self.assertEqual(enabled, runtime["enabled"])
                self.assertNotIn("error", runtime)


if __name__ == "__main__":
    unittest.main()
