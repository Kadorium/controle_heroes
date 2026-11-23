from unittest.mock import patch

from app.reporting.dashboard import _build_attention


def test_brl_is_not_missing_fx_but_foreign_obligation_is():
    rows = [{"id": 1, "currency": "BRL"}, {"id": 2, "currency": "EUR"}]
    args = dict(permissions={"billing:read", "treasury:fx_read"}, is_admin=False,
                date_from=None, date_to=None, currency=None, supplier_id=None)
    with patch("app.reporting.dashboard.billing_public.payables_queue", return_value={"items": []}), \
         patch("app.reporting.dashboard._ap_queue", return_value={"items": rows}), \
         patch("app.reporting.dashboard.treasury_public.fx.get_current_plans_bulk", return_value={}):
        result = _build_attention(None, **args)
    missing = [row for row in result["items"] if row["item_type"] == "missing_fx"]
    assert len(missing) == 1
    assert missing[0]["title"] == "1 obrigação(ões) sem taxa projetada"
    with patch("app.reporting.dashboard.billing_public.payables_queue", return_value={"items": []}), \
         patch("app.reporting.dashboard._ap_queue", return_value={"items": rows[:1]}), \
         patch("app.reporting.dashboard.treasury_public.fx.get_current_plans_bulk", return_value={}):
        result = _build_attention(None, **args)
    assert not any(row["item_type"] == "missing_fx" for row in result["items"])
