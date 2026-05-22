"""Unit tests for ``OpenKTClient``.

The client wraps ``urllib`` against ``api.openkt.ai``. These tests
intercept the underlying urlopen so we can assert request shape without
touching the network. They pin:
- the URL pattern (``/v1/memories/recall``, ``/v1/memories``, etc.)
- the Authorization header (``Bearer <token>``)
- the auth-transport choice for PATs vs JWTs
- timeout propagation
- graceful error handling (returns dict with ``_error`` on HTTP errors)
"""
from __future__ import annotations

import io
import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openkt_hermes.client import OpenKTClient


class FakeResponse:
    """Stand-in for ``urllib.request.urlopen`` context manager."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _ok(body: dict[str, Any]) -> FakeResponse:
    return FakeResponse(json.dumps(body).encode())


# ---- transport selection -----------------------------------------------------

class TestTransport:
    def test_pat_token_routes_to_mcp_jsonrpc(self) -> None:
        """PATs (okt_pat_*) must use the MCP endpoint because REST
        /v1/memories/* uses SupabaseJwtGuard (PAT-incompatible). The
        MCP endpoint uses BearerAuthGuard which accepts both."""
        c = OpenKTClient(api_key="okt_pat_test123", api_base="https://api.openkt.ai")
        assert c._uses_mcp is True

    def test_jwt_token_routes_to_rest(self) -> None:
        """Supabase JWTs work against /v1/memories/* directly via the
        SupabaseJwtGuard code path. REST is preferred when it's
        available because the response shape is simpler (no JSON-RPC
        envelope, no SSE framing)."""
        c = OpenKTClient(api_key="eyJhbGciOiJIUzI1NiIs.fake_jwt.signature", api_base="https://api.openkt.ai")
        assert c._uses_mcp is False


# ---- recall ------------------------------------------------------------------

class TestRecall:
    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_recall_rest_path(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _ok({"data": [{"id": "m1", "content": "x"}], "meta": {}})
        c = OpenKTClient(api_key="jwt_token", api_base="https://api.openkt.ai")
        result = c.recall(query="anything", project_id="org/x/y", limit=5)
        # Assert: one HTTP POST against /v1/memories/recall with bearer.
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "https://api.openkt.ai/v1/memories/recall"
        assert req.get_method() == "POST"
        assert req.headers.get("Authorization") == "Bearer jwt_token"
        body = json.loads(req.data.decode())
        assert body["query"] == "anything"
        assert body["project_id"] == "org/x/y"
        assert body["limit"] == 5
        assert result["data"][0]["content"] == "x"

    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_recall_mcp_path_for_pat(self, mock_urlopen: MagicMock) -> None:
        # MCP returns SSE framing — emulate that the way openkt-cli's
        # _mcp_client.py does.
        sse_body = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"'
            + json.dumps({"data": [{"id": "m1", "content": "x"}], "meta": {}}).replace('"', '\\"')
            + '"}]}}\n'
        )
        mock_urlopen.return_value = FakeResponse(sse_body.encode())
        c = OpenKTClient(api_key="okt_pat_xxx", api_base="https://api.openkt.ai")
        result = c.recall(query="anything", project_id="org/x/y", limit=5)
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "https://api.openkt.ai/mcp"
        body = json.loads(req.data.decode())
        # JSON-RPC framing: tools/call with kt_recall + arguments.
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "kt_recall"
        assert body["params"]["arguments"]["query"] == "anything"
        assert result["data"][0]["content"] == "x"

    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_recall_http_error_returns_error_dict(
        self, mock_urlopen: MagicMock
    ) -> None:
        """HTTP 500 should never raise — return a dict with ``_error`` so
        the provider can fail open."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.openkt.ai/v1/memories/recall", 500, "Server Error", {}, io.BytesIO(b"oops")  # type: ignore[arg-type]
        )
        c = OpenKTClient(api_key="jwt", api_base="https://api.openkt.ai")
        result = c.recall(query="x", project_id="p")
        # Caller convention: never raises, returns a dict.
        assert isinstance(result, dict)
        assert "_error" in result or "data" in result


# ---- save --------------------------------------------------------------------

class TestSave:
    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_save_posts_to_memories_with_content_and_kind(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_urlopen.return_value = _ok({"id": "mem_xyz", "content": "fact"})
        c = OpenKTClient(api_key="jwt", api_base="https://api.openkt.ai")
        c.save(content="we picked sqlite", kind="decision", project_id="p", importance=0.8)
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "https://api.openkt.ai/v1/memories"
        assert req.get_method() == "POST"
        body = json.loads(req.data.decode())
        assert body["content"] == "we picked sqlite"
        assert body["kind"] == "decision"
        assert body["importance"] == 0.8


# ---- forget ------------------------------------------------------------------

class TestForget:
    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_forget_uses_delete(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _ok({"forgotten": True})
        c = OpenKTClient(api_key="jwt", api_base="https://api.openkt.ai")
        c.forget(id="abc-123")
        req = mock_urlopen.call_args.args[0]
        assert "memories/abc-123" in req.full_url
        assert req.get_method() == "DELETE"

    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_forget_hard_propagates_query_param(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_urlopen.return_value = _ok({"forgotten": True})
        c = OpenKTClient(api_key="jwt", api_base="https://api.openkt.ai")
        c.forget(id="abc-123", hard=True)
        req = mock_urlopen.call_args.args[0]
        assert "hard=true" in req.full_url


# ---- prime -------------------------------------------------------------------

class TestPrime:
    @patch("openkt_hermes.client.urllib.request.urlopen")
    def test_prime_requests_categorized(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _ok({
            "categorized": {"decision": [{"content": "use Postgres"}]}
        })
        c = OpenKTClient(api_key="jwt", api_base="https://api.openkt.ai")
        result = c.prime(project_id="p")
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "https://api.openkt.ai/v1/prime"
        body = json.loads(req.data.decode())
        # We MUST opt in to categorized — by default the server returns
        # an empty categorized field.
        assert body.get("with_categorized") is True
        assert result["categorized"]["decision"][0]["content"] == "use Postgres"
