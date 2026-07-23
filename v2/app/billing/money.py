from decimal import ROUND_HALF_UP, Decimal

from app.billing.errors import InvoiceValidationError

QTY_QUANT = Decimal("0.0001")
COMMERCIAL_QUANT = Decimal("0.01")


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def require_positive_qty(value: str | Decimal) -> Decimal:
    qty = parse_decimal(value if not isinstance(value, str) else value)
    if qty is None or qty <= 0:
        raise InvoiceValidationError("Quantidade deve ser > 0")
    return qty.quantize(QTY_QUANT)


def money2(value: Decimal) -> Decimal:
    return value.quantize(COMMERCIAL_QUANT, rounding=ROUND_HALF_UP)


def decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def compute_line(
    *,
    quantity: Decimal,
    unit_price_gross: Decimal,
    discount_type: str | None,
    discount_unit_amount: Decimal | None,
    discount_percent: Decimal | None,
) -> tuple[Decimal, Decimal | None, Decimal | None]:
    """Retorna (gross, discount, net). discount/net None se tipo indefinido."""
    gross = money2(quantity * unit_price_gross)
    if discount_type is None or discount_type == "":
        return gross, None, None
    if discount_type == "NONE":
        disc = Decimal("0.00")
    elif discount_type == "UNIT_AMOUNT":
        if discount_unit_amount is None:
            raise InvoiceValidationError("Desconto unitário obrigatório para UNIT_AMOUNT")
        if discount_unit_amount < 0:
            raise InvoiceValidationError("Desconto unitário não pode ser negativo")
        disc = money2(quantity * discount_unit_amount)
    elif discount_type == "PERCENT":
        if discount_percent is None:
            raise InvoiceValidationError("Percentual de desconto obrigatório para PERCENT")
        if discount_percent < 0 or discount_percent > 100:
            raise InvoiceValidationError("Percentual de desconto deve estar entre 0 e 100")
        disc = money2(gross * discount_percent / Decimal("100"))
    else:
        raise InvoiceValidationError(f"Tipo de desconto inválido: {discount_type}")
    if disc > gross:
        raise InvoiceValidationError("Desconto da linha supera o bruto")
    net = money2(gross - disc)
    return gross, disc, net


def split_scadenze_percent(net: Decimal, percents: list[Decimal]) -> list[Decimal]:
    if not percents:
        raise InvoiceValidationError("Informe ao menos uma scadenza")
    total_pct = sum(percents)
    if total_pct != Decimal("100"):
        raise InvoiceValidationError("Percentuais das scadenze devem somar 100%")
    amounts: list[Decimal] = []
    allocated = Decimal("0.00")
    for i, pct in enumerate(percents):
        if pct <= 0:
            raise InvoiceValidationError("Percentual de scadenza deve ser > 0")
        if i == len(percents) - 1:
            amounts.append(money2(net - allocated))
        else:
            part = money2(net * pct / Decimal("100"))
            amounts.append(part)
            allocated += part
    if sum(amounts) != net:
        # force residual already on last; assert consistency
        amounts[-1] = money2(net - sum(amounts[:-1]))
    return amounts


def validate_amount_terms(net: Decimal, amounts: list[Decimal]) -> list[Decimal]:
    if not amounts:
        raise InvoiceValidationError("Informe ao menos uma scadenza")
    normalized = [money2(a) for a in amounts]
    if any(a <= 0 for a in normalized):
        raise InvoiceValidationError("Valor de scadenza deve ser > 0")
    if sum(normalized) != net:
        raise InvoiceValidationError(
            f"Soma das scadenze ({sum(normalized)}) deve igualar o líquido da fatura ({net})"
        )
    return normalized


def line_derived(item) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Totais derivados de InvoiceItem (gross, discount, net)."""
    if item.unit_price_gross is None:
        return None, None, None
    return compute_line(
        quantity=item.quantity,
        unit_price_gross=item.unit_price_gross,
        discount_type=item.discount_type,
        discount_unit_amount=item.discount_unit_amount,
        discount_percent=item.discount_percent,
    )


def invoice_net(items) -> Decimal | None:
    total = Decimal("0.00")
    for item in items:
        _g, _d, net = line_derived(item)
        if net is None:
            return None
        total += net
    return money2(total) if items else Decimal("0.00")
