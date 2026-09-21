"""Thin Jev SystemOne client — wraps POST /v1/systemone.

Use via apps/api/app/services/jev_service.py in the API.
Direct import is allowed for worker/scripts.
"""
from .client import JevClient

__all__ = ["JevClient"]
