"""HTTPS-only provider transport; no automatic request retries or redirects."""

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .core import CommerceError
from .validation import https_url


BASES = {'minimax': 'https://api.minimax.cn', 'seedance': 'https://ark.cn-beijing.volces.com',
         'seedream': 'https://ark.cn-beijing.volces.com', 'openai': 'https://api.openai.com',
         'chanmama': 'https://open-api.chanjing.cc', 'youcloud': 'https://console.dam.youcloud.com'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CommerceError('HTTP redirect refused; credentials were not forwarded')


class HTTP:
    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect)

    def _open(self, provider, path, body=None, headers=None, timeout=60):
        if provider not in BASES or not path.startswith('/') or path.startswith('//'):
            raise CommerceError('Unknown provider endpoint')
        data = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        if data is not None and len(data) > 64 * 1024 * 1024:
            raise CommerceError('Request exceeds 64 MB; use authorized HTTPS media URLs')
        h = {'Content-Type': 'application/json', **(headers or {})}
        req = urllib.request.Request(BASES[provider] + path, data=data, headers=h,
                                     method='GET' if data is None else 'POST')
        try:
            return self.opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            # Never log raw bodies/headers: vendor errors can echo sensitive request data.
            raise CommerceError('Provider HTTP error ' + str(e.code)) from e
        except urllib.error.URLError as e:
            raise CommerceError('Provider connection failed; inspect the original task before resubmitting') from e

    def json(self, provider, path, body=None, headers=None, timeout=60):
        with self._open(provider, path, body, headers, timeout) as response:
            raw = response.read(100 * 1024 * 1024 + 1)
        if len(raw) > 100 * 1024 * 1024:
            raise CommerceError('Provider JSON response too large')
        try:
            result = json.loads(raw)
        except ValueError as e:
            raise CommerceError('Provider returned malformed JSON') from e
        if not isinstance(result, dict):
            raise CommerceError('Provider response must be a JSON object')
        if result.get('error'):
            raise CommerceError('Provider returned an API error; inspect its console')
        base = result.get('base_resp', {})
        if base.get('status_code', 0) != 0:
            raise CommerceError('Provider business error ' + str(base.get('status_code')))
        return result

    def ndjson(self, provider, path, body, headers=None, timeout=650):
        with self._open(provider, path, body, headers, timeout) as response:
            total = 0
            for line in response:
                total += len(line)
                if total > 20 * 1024 * 1024:
                    raise CommerceError('Analysis stream exceeds 20 MB')
                yield line.decode('utf-8')

    def download(self, url, target, max_bytes=512 * 1024 * 1024):
        https_url(url)
        host = urlparse(url).hostname
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise CommerceError('Artifact download must target a public HTTPS host')
        # Signed redirects require a new explicitly inspected URL rather than credential forwarding.
        created = False
        try:
            with self.opener.open(url, timeout=60) as response, target.open('xb') as out:
                created = True
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise CommerceError('Artifact download exceeds size limit')
                    out.write(chunk)
        except Exception:
            if created:
                target.unlink(missing_ok=True)
            raise
        return total

    def put_file(self, url, path):
        https_url(url)
        host = urlparse(url).hostname
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise CommerceError('Staging target must be a public HTTPS host')
        # Presigned PUT auth stays in this URL. Never forward service API keys to storage.
        data = path.read_bytes()
        req = urllib.request.Request(url, data=data, method='PUT')
        try:
            with self.opener.open(req, timeout=180) as response:
                if not 200 <= response.status < 300:
                    raise CommerceError('Storage did not accept the upload')
        except urllib.error.HTTPError as e:
            raise CommerceError('Storage upload HTTP error ' + str(e.code)) from e
