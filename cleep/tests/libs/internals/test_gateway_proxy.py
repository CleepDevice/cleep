#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for Desktop-only gateway proxy helpers (no full Cleep session)."""

import sys
import unittest
from unittest.mock import MagicMock, patch

# bottle is only needed for HTTPResponse; stub it for host unit tests
sys.modules.setdefault("bottle", MagicMock())
_fake_bottle = sys.modules["bottle"]


class _FakeHTTPResponse:
    def __init__(self, status=200, body="", headers=None):
        self.status_code = status
        self.status = status
        self.body = body
        self.headers = headers or {}


_fake_bottle.HTTPResponse = _FakeHTTPResponse

from cleep.libs.internals.gateway_proxy import (  # noqa: E402
    build_gateway_handler,
    filter_request_headers,
    peer_base_url,
)


class TestsGatewayProxy(unittest.TestCase):
    def test_peer_base_url_https(self):
        self.assertEqual(
            peer_base_url({"ip": "192.168.1.10", "port": 443, "ssl": True}),
            "https://192.168.1.10:443",
        )

    def test_filter_drops_gateway_headers(self):
        headers = MagicMock()
        headers.keys.return_value = [
            "Authorization",
            "X-Cleep-Gateway-Auth",
            "X-Cleep-Gateway-Target",
            "Host",
        ]
        headers.get.side_effect = lambda k: {
            "Authorization": "Basic abc",
            "X-Cleep-Gateway-Auth": "tok",
            "X-Cleep-Gateway-Target": "uuid",
            "Host": "public.ngrok.app",
        }[k]
        out = filter_request_headers(
            headers,
            {"host", "x-cleep-gateway-auth", "x-cleep-gateway-target"},
        )
        self.assertEqual(out, {"Authorization": "Basic abc"})

    def test_handler_allows_pass_when_tunnel_closed(self):
        handler = build_gateway_handler(
            is_tunnel_open=lambda: False,
            get_token=lambda: "secret",
            list_peers=lambda: [],
            get_self_uuid=lambda: "self",
            auth_header="X-Cleep-Gateway-Auth",
            target_header="X-Cleep-Gateway-Target",
            peers_path="/gw/_peers",
        )
        req = MagicMock()
        self.assertIsNone(handler(req))

    def test_handler_rejects_missing_token(self):
        handler = build_gateway_handler(
            is_tunnel_open=lambda: True,
            get_token=lambda: "secret",
            list_peers=lambda: [],
            get_self_uuid=lambda: "self",
            auth_header="X-Cleep-Gateway-Auth",
            target_header="X-Cleep-Gateway-Target",
            peers_path="/gw/_peers",
        )
        req = MagicMock()
        req.get_header.return_value = None
        req.path = "/"
        resp = handler(req)
        self.assertEqual(resp.status_code, 403)

    def test_handler_peers_path(self):
        peers = [{"uuid": "p1", "hostname": "pi", "online": True}]
        handler = build_gateway_handler(
            is_tunnel_open=lambda: True,
            get_token=lambda: "secret",
            list_peers=lambda: peers,
            get_self_uuid=lambda: "self",
            auth_header="X-Cleep-Gateway-Auth",
            target_header="X-Cleep-Gateway-Target",
            peers_path="/gw/_peers",
        )
        req = MagicMock()
        req.get_header.side_effect = lambda name: (
            "secret" if "Auth" in name else None
        )
        req.path = "/gw/_peers"
        req.method = "GET"
        resp = handler(req)
        self.assertEqual(resp.status_code, 200)
        body = resp.body if isinstance(resp.body, str) else resp.body.decode()
        self.assertIn("p1", body)

    @patch("cleep.libs.internals.gateway_proxy.proxy_request_to_peer")
    def test_handler_proxies_known_peer(self, proxy_mock):
        proxy_mock.return_value = MagicMock(status_code=200)
        peer = {
            "uuid": "peer-a",
            "hostname": "a",
            "ip": "192.168.1.2",
            "port": 443,
            "ssl": True,
            "online": True,
            "cleepdesktop": False,
        }
        handler = build_gateway_handler(
            is_tunnel_open=lambda: True,
            get_token=lambda: "secret",
            list_peers=lambda: [peer],
            get_self_uuid=lambda: "self",
            auth_header="X-Cleep-Gateway-Auth",
            target_header="X-Cleep-Gateway-Target",
            peers_path="/gw/_peers",
        )
        req = MagicMock()
        req.get_header.side_effect = lambda name: (
            "secret" if "Auth" in name else "peer-a" if "Target" in name else None
        )
        req.path = "/command"
        resp = handler(req)
        proxy_mock.assert_called_once()
        self.assertEqual(resp.status_code, 200)

    def test_handler_unknown_peer_404(self):
        handler = build_gateway_handler(
            is_tunnel_open=lambda: True,
            get_token=lambda: "secret",
            list_peers=lambda: [],
            get_self_uuid=lambda: "self",
            auth_header="X-Cleep-Gateway-Auth",
            target_header="X-Cleep-Gateway-Target",
            peers_path="/gw/_peers",
        )
        req = MagicMock()
        req.get_header.side_effect = lambda name: (
            "secret" if "Auth" in name else "missing" if "Target" in name else None
        )
        req.path = "/"
        resp = handler(req)
        self.assertEqual(resp.status_code, 404)
