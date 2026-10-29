#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Desktop-only LAN gateway helpers for CleepRemoteAccessModule.

Token gate + reverse-proxy to bus peers. Tunnel providers (ngrok, …) only
publish a public URL; this module owns the house proxy.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import requests

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


def filter_request_headers(headers, drop_names):
    """
    Copy request headers, dropping hop-by-hop and gateway control headers.

    Args:
        headers: bottle/werkzeug header mapping
        drop_names (set[str]): lowercase header names to drop

    Returns:
        dict: headers for the upstream request
    """
    out = {}
    drop = {n.lower() for n in drop_names} | HOP_BY_HOP
    for key in headers.keys():
        if key.lower() in drop:
            continue
        out[key] = headers.get(key)
    return out


def filter_response_headers(headers):
    """
    Filter upstream response headers for Bottle.

    Args:
        headers: requests response headers

    Returns:
        dict: safe response headers
    """
    out = {}
    for key, value in headers.items():
        if key.lower() in HOP_BY_HOP:
            continue
        out[key] = value
    return out


def peer_base_url(peer):
    """
    Build ``http(s)://ip:port`` for a peer dict from get_peers.

    Args:
        peer (dict): peer infos

    Returns:
        str|None: base URL or None if incomplete
    """
    ip = peer.get("ip")
    if not ip:
        return None
    port = int(peer.get("port") or (443 if peer.get("ssl") else 80))
    scheme = "https" if peer.get("ssl") else "http"
    return "%s://%s:%s" % (scheme, ip, port)


def _http_response(status, body, headers=None):
    """Build a Bottle HTTPResponse (lazy import for unit tests without bottle)."""
    import bottle

    return bottle.HTTPResponse(status=status, body=body, headers=headers or {})


def proxy_request_to_peer(request, peer, timeout=60, verify_ssl=False):
    """
    Reverse-proxy the current Bottle request to a LAN peer.

    Args:
        request: bottle request
        peer (dict): peer infos (ip, port, ssl)
        timeout (float): upstream timeout
        verify_ssl (bool): verify peer TLS cert (device certs are self-signed)

    Returns:
        bottle.HTTPResponse: proxied response
    """
    base = peer_base_url(peer)
    if not base:
        return _http_response(502, "Peer has no address")

    path = request.path or "/"
    query = request.query_string
    url = base + path
    if query:
        url = url + "?" + query

    drop = {
        "host",
        "content-length",
        "x-cleep-gateway-auth",
        "x-cleep-gateway-target",
    }
    headers = filter_request_headers(request.headers, drop)
    body = request.body.read() if request.method in ("POST", "PUT", "PATCH") else None

    try:
        upstream = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=body,
            stream=True,
            timeout=timeout,
            allow_redirects=False,
            verify=verify_ssl,
        )
    except requests.RequestException as exc:
        return _http_response(502, "Upstream error: %s" % exc)

    return _http_response(
        upstream.status_code,
        upstream.raw,
        filter_response_headers(upstream.headers),
    )


def make_json_response(payload, status=200):
    """
    Build a JSON HTTPResponse.

    Args:
        payload (Any): JSON-serializable body
        status (int): HTTP status

    Returns:
        bottle.HTTPResponse
    """
    return _http_response(
        status,
        json.dumps(payload),
        {"Content-Type": "application/json"},
    )


def build_gateway_handler(
    is_tunnel_open: Callable[[], bool],
    get_token: Callable[[], str | None],
    list_peers: Callable[[], list[dict[str, Any]]],
    get_self_uuid: Callable[[], str | None],
    auth_header: str,
    target_header: str,
    peers_path: str,
    logger=None,
):
    """
    Build a rpcserver gateway handler for loopback tunnel traffic.

    Returns:
        callable: ``handler(request) -> HTTPResponse|None``
    """

    def handler(request):
        if not is_tunnel_open():
            return None

        expected = get_token()
        get_header = getattr(request, "get_header", None)
        if callable(get_header):
            provided = get_header(auth_header)
            target = get_header(target_header)
        else:
            provided = request.headers.get(auth_header) or request.headers.get(
                auth_header.lower()
            )
            target = request.headers.get(target_header) or request.headers.get(
                target_header.lower()
            )
        if not expected or provided != expected:
            if logger:
                logger.warning("Gateway rejected request without valid Desktop token")
            return _http_response(403, "Forbidden")

        path = request.path or "/"
        if path.rstrip("/") == peers_path.rstrip("/"):
            if request.method != "GET":
                return _http_response(405, "Method not allowed")
            return make_json_response({"peers": list_peers()})
        self_uuid = get_self_uuid()
        if not target or (self_uuid and target == self_uuid):
            return None

        peers_by_uuid = {p.get("uuid"): p for p in list_peers() if p.get("uuid")}
        peer = peers_by_uuid.get(target)
        if not peer:
            return _http_response(404, "Unknown peer")
        if peer.get("cleepdesktop"):
            return _http_response(404, "Unknown peer")
        if not peer.get("online", True):
            return _http_response(502, "Peer offline")

        return proxy_request_to_peer(request, peer)

    return handler
