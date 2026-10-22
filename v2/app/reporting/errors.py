"""Erros do package Reporting (sem import de foundation)."""

from __future__ import annotations


class ReportingError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "reporting_error",
        status_code: int = 400,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
