import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from commerce_core.core import CommerceError
from commerce_core.http import HTTP


def addresses(ip):
    return [(2, 1, 6, '', (ip, 443))]


class NetworkDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / 'v.mp4'

    def connection(self, status=200, body=b'media'):
        test = self
        class Response(io.BytesIO):
            pass
        class Connection:
            def __init__(self, host, ip):
                test.assertEqual(host, 'cdn.example')
                test.assertEqual(ip, '8.8.8.8')
            def request(self, method, path, **kwargs):
                test.assertEqual(method, 'GET')
                test.assertEqual(path, '/v.mp4?signature=synthetic')
                test.assertNotIn('Authorization', kwargs.get('headers', {}))
            def getresponse(self):
                response = Response(body)
                response.status = status
                return response
            def close(self):
                pass
        return Connection

    def test_public_dns_is_pinned_no_second_unchecked_resolution(self):
        with patch('commerce_core.http.socket.getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch('commerce_core.http.PinnedHTTPSConnection', self.connection()):
            HTTP().download('https://cdn.example/v.mp4?signature=synthetic', self.target)
        self.assertEqual(self.target.read_bytes(), b'media')

    def test_tun_fake_dns_requires_explicit_public_resolution(self):
        with patch('commerce_core.http.socket.getaddrinfo', return_value=addresses('198.18.0.189')):
            with self.assertRaises(CommerceError):
                HTTP().download('https://cdn.example/v.mp4', self.target)
        self.assertFalse(self.target.exists())

    def test_explicit_fake_dns_fallback_still_rejects_private_answers(self):
        for answer, allowed in [('8.8.8.8', True), ('127.0.0.1', False)]:
            transport = HTTP(public_dns=True)
            with patch('commerce_core.http.socket.getaddrinfo', return_value=addresses('198.18.0.189')), \
                 patch.object(transport, 'resolve_public', return_value=[answer]), \
                 patch('commerce_core.http.PinnedHTTPSConnection', self.connection()):
                if allowed:
                    transport.download('https://cdn.example/v.mp4?signature=synthetic', self.target)
                    self.target.unlink()
                else:
                    with self.assertRaises(CommerceError):
                        transport.download('https://cdn.example/v.mp4', self.target)

    def test_real_private_destinations_and_nonstandard_ports_never_get_fallback(self):
        for url in ['https://cdn.example/v.mp4', 'https://cdn.example:8443/v.mp4']:
            transport = HTTP(public_dns=True)
            with patch('commerce_core.http.socket.getaddrinfo', return_value=addresses('192.168.1.1')), \
                 patch.object(transport, 'resolve_public') as resolve:
                with self.assertRaises(CommerceError):
                    transport.download(url, self.target)
                resolve.assert_not_called()

    def test_redirect_and_size_limit_never_leave_accepted_partial_file(self):
        for status, maximum in [(302, 1024), (200, 1)]:
            with patch('commerce_core.http.socket.getaddrinfo', return_value=addresses('8.8.8.8')), \
                 patch('commerce_core.http.PinnedHTTPSConnection', self.connection(status)):
                with self.assertRaises(CommerceError):
                    HTTP().download('https://cdn.example/v.mp4?signature=synthetic', self.target, max_bytes=maximum)
            self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
