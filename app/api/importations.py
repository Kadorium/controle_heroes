from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import IMPORTATION_TRANSITIONS
from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationItem, ImportationOrder, Product, Supplier, User
from app.schemas_import import (
    AllowedTransitionItem,
    AllowedTransitionsResponse,
    BrazilOperationalNotesUpdate,
    CancelRequest,
    ImportationCreate,
    ImportationItemCreate,
    ImportationItemMappingUpdate,
    ImportationItemResponse,
    ImportationResponse,
    ItalyFieldOverrideRequest,
    ItalyFieldOverrideResponse,
    LinkHeroesRawRequest,
    LinkHeroesRawResponse,
    HeroesImportPreviewRequest,
    HeroesImportCommitRequest,
    HeroesImportRunResponse,
    StatusTransitionRequest,
)
from app.schemas_order_central import OrderCentralResponse, OrderQueueResponse
from app.services.auth import write_audit_log
from app.services.importation_guard import ImportationLockedError, assert_importation_editable
from app.services.italy_override import ItalyOverrideError, apply_italy_field_override
from app.services.finance import register_exchange_rate
from app.services.order_central import build_order_central, build_order_queue
from app.services.product_catalog import ProductReadinessError, validate_product_for_usage
from app.services.heroes_xlsx_import import link_raw_file_to_importation, preview_attached_run
from app.services.heroes_xlsx_commit import commit_merge_heroes_run
from app.services.status import (
    InvalidStatusTransition,
    check_required_documents,
    transition_importation_status,
    validate_transition,
)

router = APIRouter(prefix="/importations", tags=["importations"])


def _validate_item_product(db: Session, payload: ImportationItemCreate) -> None:
    if not payload.product_id:
        return
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    try:
        validate_product_for_usage(
            db,
            product,
            "importation",
            allow_discontinued_override=bool(payload.discontinued_override_reason),
            override_reason=payload.discontinued_override_reason,
        )
    except ProductReadinessError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("", response_model=list[ImportationResponse])
def list_importations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    include_inactive: bool = False,
):
    q = db.query(ImportationOrder)
    if not include_inactive:
        q = q.filter(ImportationOrder.is_active.is_(True))
    return q.order_by(ImportationOrder.created_at.desc()).all()


@router.get("/order-queue", response_model=OrderQueueResponse)
def get_order_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    limit: int = 100,
):
    return build_order_queue(db, limit=limit)


@router.post("", response_model=ImportationResponse, status_code=status.HTTP_201_CREATED)
def create_importation(
    payload: ImportationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.is_active.is_(True)).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    if db.query(ImportationOrder).filter(ImportationOrder.po_number == payload.po_number).first():
        raise HTTPException(status_code=409, detail="Já existe uma ordem com esse número.")

    imp = ImportationOrder(
        po_number=payload.po_number,
        supplier_id=payload.supplier_id,
        currency=payload.currency,
        incoterm=payload.incoterm,
        estimated_total=payload.estimated_total,
        current_status="PO_CREATED",
        created_by_id=current_user.id,
    )
    db.add(imp)
    db.flush()

    for item_data in payload.items:
        _validate_item_product(db, item_data)
        db.add(ImportationItem(importation_id=imp.id, **item_data.model_dump(exclude={"discontinued_override_reason"})))

    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_order",
        entity_id=str(imp.id),
        action="create",
    )
    db.commit()
    db.refresh(imp)

    if payload.opening_exchange_rate is not None:
        register_exchange_rate(
            db,
            currency_from=payload.currency,
            rate_type="OPENING_PROVISION",
            rate_value=payload.opening_exchange_rate,
            user_id=current_user.id,
            importation_id=imp.id,
            comment="Câmbio provisionado na abertura da ordem",
        )

    return imp


@router.get("/{importation_id}", response_model=ImportationResponse)
def get_importation(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return imp


@router.get("/{importation_id}/order-central", response_model=OrderCentralResponse)
def get_order_central(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    try:
        return build_order_central(db, importation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{importation_id}/items", response_model=list[ImportationItemResponse])
def list_items(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )


@router.post("/{importation_id}/items", response_model=ImportationItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    importation_id: int,
    payload: ImportationItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    _validate_item_product(db, payload)
    item = ImportationItem(
        importation_id=importation_id,
        **payload.model_dump(exclude={"discontinued_override_reason"}),
    )
    db.add(item)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_item",
        entity_id=str(importation_id),
        action="add_item",
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{importation_id}/allowed-transitions", response_model=AllowedTransitionsResponse)
def get_allowed_transitions(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    candidates = IMPORTATION_TRANSITIONS.get(imp.current_status, [])
    transitions: list[AllowedTransitionItem] = []
    for st in candidates:
        try:
            validate_transition(imp.current_status, st)
            check_required_documents(db, importation_id, st)
            transitions.append(AllowedTransitionItem(status=st, blocked=False, block_reason=None))
        except InvalidStatusTransition as e:
            transitions.append(AllowedTransitionItem(status=st, blocked=True, block_reason=str(e)))
    return AllowedTransitionsResponse(current_status=imp.current_status, transitions=transitions)


@router.post("/{importation_id}/transition", response_model=ImportationResponse)
def transition_status(
    importation_id: int,
    payload: StatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    try:
        return transition_importation_status(
            db, imp, payload.new_status, user_id=current_user.id, reason=payload.reason
        )
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{importation_id}/brazil-fields", response_model=ImportationResponse)
def update_brazil_fields(
    importation_id: int,
    payload: BrazilOperationalNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return imp
    for field, new_value in changes.items():
        old_value = getattr(imp, field, None)
        if old_value == new_value:
            continue
        setattr(imp, field, new_value)
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="importation_order",
            entity_id=str(imp.id),
            action="update_brazil_field",
            field_changed=field,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
        )
    db.commit()
    db.refresh(imp)
    return imp


@router.post(
    "/{importation_id}/link-heroes-raw",
    response_model=LinkHeroesRawResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_heroes_raw_to_importation(
    importation_id: int,
    payload: LinkHeroesRawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    try:
        run = link_raw_file_to_importation(
            db,
            importation_id=importation_id,
            raw_file_id=payload.raw_file_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LinkHeroesRawResponse(
        run_id=run.id,
        raw_file_id=run.raw_file_id,
        importation_id=run.importation_id,
        status=run.status,
    )


def _heroes_run_response(run) -> HeroesImportRunResponse:
    preview = run.preview_json or {}
    return HeroesImportRunResponse(
        run_id=run.id,
        importation_id=run.importation_id,
        status=run.status,
        sheet_name=run.sheet_name,
        preview=preview,
        warnings=run.warnings_json,
        errors=run.errors_json,
        sku_review_pending=bool(preview.get("sku_review_pending")),
        sku_review_open_count=int(preview.get("sku_review_open_count") or 0),
        sku_review_line_count=int(preview.get("sku_review_line_count") or 0),
        merge_warnings=list(preview.get("merge_warnings") or []),
    )


@router.get(
    "/{importation_id}/heroes-import/preview",
    response_model=HeroesImportRunResponse,
)
def preview_heroes_import_for_order(
    importation_id: int,
    sheet_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        run = preview_attached_run(
            db,
            importation_id=importation_id,
            user_id=current_user.id,
            sheet_name=sheet_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _heroes_run_response(run)


@router.post(
    "/{importation_id}/heroes-import/commit",
    response_model=HeroesImportRunResponse,
)
def commit_heroes_import_for_order(
    importation_id: int,
    payload: HeroesImportCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    from app.services.heroes_xlsx_import import find_attached_run_for_importation

    run = find_attached_run_for_importation(db, importation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Vínculo Heroes não encontrado")
    try:
        commit_merge_heroes_run(
            db,
            run.id,
            user_id=current_user.id,
            category_overrides=payload.category_overrides,
            confirm_import=payload.confirm_import,
            confirm_sheet_match=payload.confirm_sheet_match,
        )
        db.refresh(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _heroes_run_response(run)


@router.patch("/{importation_id}/items/{item_id}", response_model=ImportationItemResponse)
def update_item_mapping(
    importation_id: int,
    item_id: int,
    payload: ImportationItemMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    item = db.query(ImportationItem).filter(
        ImportationItem.id == item_id,
        ImportationItem.importation_id == importation_id,
        ImportationItem.is_active.is_(True),
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item da ordem não encontrado")
    changes = payload.model_dump(exclude_unset=True)
    for field, new_value in changes.items():
        old_value = getattr(item, field, None)
        if old_value == new_value:
            continue
        setattr(item, field, new_value)
        write_audit_log(
            db,
            user_id=current_user.id,
            entity_type="importation_item",
            entity_id=str(item.id),
            action="update_item_mapping",
            field_changed=field,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
        )
    db.commit()
    db.refresh(item)
    return item


@router.post("/{importation_id}/italy-overrides", response_model=ItalyFieldOverrideResponse)
def italy_field_override(
    importation_id: int,
    payload: ItalyFieldOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    try:
        result = apply_italy_field_override(
            db,
            importation_id=importation_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            field_name=payload.field_name,
            new_value=payload.new_value,
            reason=payload.reason,
            attachment_id=payload.attachment_id,
            user_id=current_user.id,
        )
        return ItalyFieldOverrideResponse(**result)
    except ItalyOverrideError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{importation_id}/cancel", response_model=ImportationResponse)
def cancel_importation(
    importation_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    imp.is_active = False
    imp.cancelled_at = datetime.now(timezone.utc)
    imp.cancelled_by_id = current_user.id
    imp.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_order",
        entity_id=str(imp.id),
        action="cancel",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(imp)
    return imp
