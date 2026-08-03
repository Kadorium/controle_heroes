"""Fachada pública Reporting — somente leitura."""

from app.reporting.queries import ap_queue, order_cockpit, orders_list

__all__ = ["ap_queue", "order_cockpit", "orders_list"]
