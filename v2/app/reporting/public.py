"""Fachada pública Reporting — somente leitura."""

from app.reporting.queries import ap_queue, order_cockpit

__all__ = ["ap_queue", "order_cockpit"]
