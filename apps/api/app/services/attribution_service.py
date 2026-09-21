"""Thin wrapper — real logic lives in jev_service. Kept for import parity with plan."""
from app.services import jev_service

analyze = jev_service.analyze_trace
