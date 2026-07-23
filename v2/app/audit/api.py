"""Audit HTTP thin — listagem orquestrada em foundation.audit_routes."""

from fastapi import APIRouter

router = APIRouter(tags=["audit"])
