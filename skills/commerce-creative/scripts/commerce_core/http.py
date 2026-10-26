"""HTTPS-only provider transport; no automatic request retries or redirects."""

import ipaddress
import http.client
import json
import socket
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlencode

from .core import CommerceError
from .validation import https_url


BASES = {'minimax': 'https://api.minimax.cn', 'seedance': 'https://ark.cn-beijing.volces.com',
         'seedream': 'https://ark.cn-beijing.volces.com', 'openai': 'https://api.openai.com',
         'chanmama': 'https://open-api.chanjing.cc', 'youcloud': 'https://console.dam.youcloud.com'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CommerceError('HTTP redirect refused; credentials were not forwarded')


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, ip):
        super().__init__(host, port=443, timeout=60, context=ssl.create_default_context())
        self.public_ip = ip

    def connect(self):
        raw = socket.create_connection((self.public_ip, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class HTTP:
    def __init__(self, public_dns=False):
        self.opener = urllib.request.build_opener(NoRedirect)
        self.public_dns = public_dns

    def resolve_public(self, host):
        # Explicit opt-in sends only this artifact hostname to a fixed HTTPS resolver.
        url = 'https://dns.alidns.com/resolve?' + urlencode({'name': host, 'type': 'A'})
        with self.opener.open(url, timeout=20) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise CommerceError('Public DNS response too large')
        result = json.loads(raw)
        if result.get('Status') != 0:
            raise CommerceError('Public DNS lookup failed')
        return [a['data'] for a in result.get('Answer', []) if a.get('type') in (1, 28)]

    def storage_connection(self, url):
        https_url(url)
        parsed = urlparse(url)
        if parsed.port not in (None, 443):
            raise CommerceError('Artifact/storage HTTPS port must be 443')
        try:
            addresses = [a[4][0] for a in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)]
        except socket.gaierror as e:
            raise CommerceError('Artifact DNS failed; no request sent') from e
        fake_range = ipaddress.ip_network('198.18.0.0/15')
        fake = bool(addresses) and all(ipaddress.ip_address(a) in fake_range for a in addresses)
        if fake and self.public_dns:
            addresses = self.resolve_public(parsed.hostname)
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise CommerceError('Artifact/storage must target a public HTTPS host. For TUN fake-DNS only, explicitly choose --public-dns; no system settings changed')
        # Pin the exact validated address; do not perform another DNS lookup at connect time.
        return PinnedHTTPSConnection(parsed.hostname, addresses[0]), parsed.path + ('?' + parsed.query if parsed.query else '')

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
        connection, path = self.storage_connection(url)
        # Signed redirects require a new explicitly inspected URL rather than credential forwarding.
        created = False
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                raise CommerceError('Artifact HTTP status ' + str(response.status) + '; redirects refused')
            with response, target.open('xb') as out:
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
        finally:
            connection.close()
        return total

    def put_file(self, url, path):
        connection, target = self.storage_connection(url)
        # Presigned PUT auth stays in this URL. Never forward service API keys to storage.
        data = path.read_bytes()
        try:
            connection.request('PUT', target, body=data)
            with connection.getresponse() as response:
                if not 200 <= response.status < 300:
                    raise CommerceError('Storage did not accept the upload')
        finally:
            connection.close()
