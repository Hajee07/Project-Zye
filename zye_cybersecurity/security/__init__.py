"""Security and authorization package for ZYE Cybersecurity."""
from zye_cybersecurity.security.scan_authorizer import ScanAuthorizer, ScanAuthorizationError

__all__ = [
    "ScanAuthorizer",
    "ScanAuthorizationError",
]
