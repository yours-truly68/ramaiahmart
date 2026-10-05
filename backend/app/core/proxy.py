"""Safe proxy-aware client IP extraction.

Protects against IP spoofing: forwarded headers (X-Forwarded-For, X-Real-IP)
are only accepted if the immediate peer IP belongs to a configured trusted proxy network.
"""

import ipaddress
import logging

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_ip_in_network(ip_str: str, network_or_ip: str) -> bool:
    """Check if an IP address string matches an IP or CIDR network string."""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        net_str = network_or_ip.strip()
        if "/" in net_str:
            return ip in ipaddress.ip_network(net_str, strict=False)
        return ip == ipaddress.ip_address(net_str)
    except ValueError:
        return False


def is_trusted_proxy(client_host: str, trusted_list: list[str]) -> bool:
    """Check if the connecting host is among configured trusted reverse proxies."""
    if not client_host:
        return False
    return any(is_ip_in_network(client_host, net) for net in trusted_list)


def get_client_ip(request: Request) -> str:
    """Safely extract the real client IP address from the request.

    If request.client.host is a trusted reverse proxy (e.g. Docker Nginx gateway),
    inspects X-Real-IP or the first IP in X-Forwarded-For.
    If the direct peer is untrusted, forwarded headers are ignored to prevent spoofing.
    """
    direct_ip = request.client.host if request.client else "127.0.0.1"

    if not is_trusted_proxy(direct_ip, settings.TRUSTED_PROXIES):
        return direct_ip

    # Check X-Real-IP first (Nginx sets this explicitly to $remote_addr)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        cleaned = real_ip.strip()
        try:
            ipaddress.ip_address(cleaned)
            return cleaned
        except ValueError:
            pass

    # Fallback to leftmost IP in X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        for candidate in parts:
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                continue

    return direct_ip
