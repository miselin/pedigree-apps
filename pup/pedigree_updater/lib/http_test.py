import io
import os
import tempfile
import unittest
from email.message import Message
from unittest import mock

from . import http as pup_http


class Response(io.BytesIO):
    def __init__(self, body, charset=None):
        super().__init__(body)
        self.headers = Message()
        if charset:
            self.headers["Content-Type"] = "text/plain; charset=%s" % charset


class FakeConnection:
    instances = []

    def __init__(self, host, port=None, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.headers = {}
        self.sent = []
        self.closed = False
        self.__class__.instances.append(self)

    def putrequest(self, method, target):
        self.method = method
        self.target = target

    def putheader(self, name, value):
        self.headers[name] = value

    def endheaders(self):
        pass

    def send(self, contents):
        self.sent.append(contents)

    def getresponse(self):
        return type(
            "UploadResponse",
            (),
            {
                "status": 200,
                "read": lambda response: b"ok\n",
            },
        )()

    def close(self):
        self.closed = True


class HttpTest(unittest.TestCase):
    def setUp(self):
        FakeConnection.instances = []

    def test_copy_url_streams_response_to_target(self):
        response = Response(b"package contents")
        with mock.patch.object(
            pup_http.urllib.request,
            "urlopen",
            return_value=response,
        ) as urlopen:
            target = io.BytesIO()
            pup_http.copy_url("https://repo.example/example.pup", target)

        self.assertEqual(target.getvalue(), b"package contents")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), pup_http.USER_AGENT)

    def test_get_text_adds_legacy_upload_parameters(self):
        response = Response(b"https://upload.example/blobstore\n")
        with mock.patch.object(
            pup_http.urllib.request,
            "urlopen",
            return_value=response,
        ) as urlopen:
            result = pup_http.get_text(
                "https://repo.example/upload?existing=1",
                {"key": "upload", "key_value": "secret"},
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://repo.example/upload?existing=1&key=upload&key_value=secret",
        )
        self.assertEqual(result.strip(), "https://upload.example/blobstore")

    def test_post_multipart_streams_legacy_fields_and_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = os.path.join(temporary, "example-1.2-amd64.pup")
            with open(package, "wb") as output:
                output.write(b"package\x00contents")

            with (
                mock.patch.object(
                    pup_http.http.client,
                    "HTTPSConnection",
                    FakeConnection,
                ),
                mock.patch.object(
                    pup_http.secrets,
                    "token_hex",
                    return_value="boundary",
                ),
            ):
                result = pup_http.post_multipart(
                    "https://upload.example/blobstore?token=1",
                    {
                        "name": "example",
                        "vers": "1.2",
                        "arch": "amd64",
                        "sha1": "digest",
                    },
                    "file",
                    package,
                )

        connection = FakeConnection.instances[0]
        payload = b"".join(connection.sent)
        self.assertEqual(result.strip(), "ok")
        self.assertEqual(connection.host, "upload.example")
        self.assertEqual(connection.method, "POST")
        self.assertEqual(connection.target, "/blobstore?token=1")
        self.assertEqual(
            int(connection.headers["Content-Length"]), len(payload)
        )
        self.assertIn(b'name="name"\r\n\r\nexample\r\n', payload)
        self.assertIn(b'name="vers"\r\n\r\n1.2\r\n', payload)
        self.assertIn(
            b'filename="example-1.2-amd64.pup"',
            payload,
        )
        self.assertIn(b"package\x00contents", payload)
        self.assertTrue(payload.endswith(b"\r\n------pup-boundary--\r\n"))
        self.assertTrue(connection.closed)

    def test_non_http_urls_are_rejected(self):
        with self.assertRaisesRegex(pup_http.RequestError, "HTTP URL"):
            pup_http.copy_url("file:///etc/passwd", io.BytesIO())


if __name__ == "__main__":
    unittest.main()
