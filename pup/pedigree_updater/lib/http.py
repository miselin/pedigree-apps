import http.client
import os
import secrets
import shutil
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = "pup-client/1.2"


class RequestError(RuntimeError):
    pass


def _http_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RequestError("unsupported or incomplete HTTP URL")
    if parsed.username or parsed.password:
        raise RequestError("credentials in HTTP URLs are not supported")
    return parsed


def _request(url):
    _http_url(url)
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def _with_query(url, parameters):
    parsed = _http_url(url)
    query = urllib.parse.urlencode(parameters)
    if parsed.query and query:
        query = "%s&%s" % (parsed.query, query)
    elif parsed.query:
        query = parsed.query
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
    )


def copy_url(url, target, timeout=60):
    try:
        with urllib.request.urlopen(_request(url), timeout=timeout) as response:
            shutil.copyfileobj(response, target, length=1024 * 1024)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
        raise RequestError("failed to download %s" % url) from error


def get_text(url, parameters=None, timeout=30):
    if parameters:
        url = _with_query(url, parameters)
    try:
        with urllib.request.urlopen(_request(url), timeout=timeout) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
        raise RequestError("failed to fetch %s" % url) from error

    try:
        return body.decode(charset)
    except (LookupError, UnicodeDecodeError) as error:
        raise RequestError("invalid text response from %s" % url) from error


def _quoted_header_value(value):
    value = str(value)
    if "\r" in value or "\n" in value:
        raise RequestError("multipart names cannot contain newlines")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _multipart_prefix(boundary, fields, file_field, filename):
    sections = []
    for name, value in fields.items():
        sections.append(
            (
                '--%s\r\nContent-Disposition: form-data; name="%s"'
                "\r\n\r\n%s\r\n"
                % (
                    boundary,
                    _quoted_header_value(name),
                    value,
                )
            ).encode("utf-8")
        )
    sections.append(
        (
            '--%s\r\nContent-Disposition: form-data; name="%s"; '
            'filename="%s"\r\nContent-Type: application/octet-stream'
            "\r\n\r\n"
            % (
                boundary,
                _quoted_header_value(file_field),
                _quoted_header_value(filename),
            )
        ).encode("utf-8")
    )
    return b"".join(sections)


def post_multipart(
    url,
    fields,
    file_field,
    file_path,
    timeout=300,
):
    parsed = _http_url(url)
    boundary = "----pup-%s" % secrets.token_hex(16)
    prefix = _multipart_prefix(
        boundary,
        fields,
        file_field,
        os.path.basename(file_path),
    )
    suffix = ("\r\n--%s--\r\n" % boundary).encode("ascii")
    try:
        port = parsed.port
    except ValueError as error:
        raise RequestError("invalid port in upload URL") from error

    connection_class = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )
    request_target = parsed.path or "/"
    if parsed.query:
        request_target += "?" + parsed.query

    connection = connection_class(parsed.hostname, port=port, timeout=timeout)
    try:
        content_length = len(prefix) + os.path.getsize(file_path) + len(suffix)
        connection.putrequest("POST", request_target)
        connection.putheader("User-Agent", USER_AGENT)
        connection.putheader(
            "Content-Type",
            "multipart/form-data; boundary=%s" % boundary,
        )
        connection.putheader("Content-Length", str(content_length))
        connection.endheaders()
        connection.send(prefix)
        with open(file_path, "rb") as package:
            while True:
                chunk = package.read(1024 * 1024)
                if not chunk:
                    break
                connection.send(chunk)
        connection.send(suffix)

        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            raise RequestError(
                "upload failed with HTTP status %d" % response.status
            )
    except (OSError, http.client.HTTPException) as error:
        raise RequestError("failed to upload %s" % file_path) from error
    finally:
        connection.close()

    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RequestError("invalid text response from %s" % url) from error
