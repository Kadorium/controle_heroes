"""Identity HTTP surface is owned by Foundation (auth_routes + deps)."""

from fastapi import APIRouter

router = APIRouter(tags=["identity"])
