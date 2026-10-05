import socket
import urllib.request

import pytest

from tests.conftest import NetworkBlocked


def test_urlopen_is_blocked():
    with pytest.raises((NetworkBlocked, OSError)) as info:
        urllib.request.urlopen("https://example.com", timeout=1)
    assert "network access is not allowed" in str(info.value)


def test_raw_socket_connect_is_blocked():
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("example.com", 443))
