"""Session helpers for HACS.

This module creates an ``aiohttp.ClientSession`` that is able to read proxy
settings from the operating-system environment.  This is important for users
who can only reach ``github.com`` through a proxy.

Supported environment variables (case-insensitive, standard ``aiohttp`` /
``urllib`` names):

* ``HTTPS_PROXY`` / ``https_proxy``
* ``HTTP_PROXY`` / ``http_proxy``
* ``ALL_PROXY`` / ``all_proxy``
* ``NO_PROXY`` / ``no_proxy``
"""

from __future__ import annotations

import logging
import os

from aiohttp import ClientSession, TCPConnector

_LOGGER = logging.getLogger(__name__)

#: Common environment variable names for a generic proxy.
_PROXY_ENV_NAMES = (
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "ALL_PROXY",
    "all_proxy",
)


def _read_env_proxy() -> str | None:
    """Return the first non-empty proxy URL found in the environment."""
    for name in _PROXY_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def is_proxy_configured() -> bool:
    """Return ``True`` when *any* proxy setting is present in the environment."""
    return _read_env_proxy() is not None


def get_active_proxy_url() -> str | None:
    """Return the proxy URL that HACS would use, or ``None``."""
    return _read_env_proxy()


async def async_create_hacs_session() -> ClientSession:
    """Create an :class:`aiohttp.ClientSession` with proxy support.

    If a proxy is detected via the standard ``HTTPS_PROXY`` /
    ``HTTP_PROXY`` / ``ALL_PROXY`` variables the session is created with
    ``trust_env=True`` so that ``aiohttp`` applies it automatically.
    Certificate verification is also disabled when a proxy is active,
    because many corporate / transparent proxies perform TLS interception
    and present a self-signed certificate.

    If **no** proxy is configured the function falls back to a plain session so
    that the behaviour is identical to the original code.
    """
    proxy_url = get_active_proxy_url()

    if proxy_url is not None:
        _LOGGER.info("HACS HTTP proxy detected (%s)", proxy_url)
        # trust_env=True makes aiohttp read *_PROXY / *_proxy automatically.
        # ssl=False is intentional: most MITM/corporate proxies replace the
        # upstream certificate with their own (often self-signed) CA.
        connector = TCPConnector(ssl=False)
        session = ClientSession(trust_env=True, connector=connector)
    else:
        session = ClientSession()

    return session


async def async_close_hacs_session(
    session: ClientSession | None,
) -> None:
    """Close a session previously created by :func:`async_create_hacs_session`.

    Safe to call with ``None``.
    """
    if session is not None and not session.closed:
        await session.close()
