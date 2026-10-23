"""Stock preferences, actor isolated; independent from dashboard widget layouts."""
from sqlalchemy import text
from app.reporting.models import ReportingStockView
from app.reporting.stock_contract import StockQuery
from app.reporting.errors import ReportingError
from app.audit import public as audit

def view_dict(v):return {'id':v.id,'name':v.name,'config':v.config,'is_default':v.is_default,'version':v.version,'schema_version':v.schema_version}
def list_stock_views(db,actor_id):return [view_dict(v) for v in db.query(ReportingStockView).filter_by(actor_id=actor_id).order_by(ReportingStockView.name).all()]
def save_stock_view(db,*,actor_id,name,config,is_default=False,view_id=None,expected_version=None):
    clean=StockQuery.model_validate(config).model_dump();clean['offset']=0;clean['product_id']=None
    if not name.strip() or len(name.strip())>128:raise ReportingError('Informe um nome para a visão',code='invalid_name',status_code=422)
    db.execute(text('select pg_advisory_xact_lock(hashtext(:actor))'),{'actor':'stock-view:'+actor_id})
    row=None
    if view_id:
        row=db.query(ReportingStockView).filter_by(id=view_id,actor_id=actor_id).with_for_update().first()
        if not row:raise ReportingError('Visão não encontrada',code='not_found',status_code=404)
        if row.version!=expected_version:raise ReportingError('Esta visão mudou. Reabra antes de salvar.',code='version_conflict',status_code=409)
    other=db.query(ReportingStockView).filter_by(actor_id=actor_id,name=name.strip()).first()
    if other and (not row or other.id!=row.id):raise ReportingError('Já existe uma visão com esse nome',code='name_conflict',status_code=409)
    if is_default:db.query(ReportingStockView).filter_by(actor_id=actor_id,is_default=True).update({'is_default':False});db.flush()
    if row:row.version+=1
    else:row=ReportingStockView(actor_id=actor_id,version=1,schema_version=1);db.add(row)
    row.name=name.strip();row.config=clean;row.is_default=is_default;db.flush()
    audit.record_event(db,actor_id=actor_id,entity_type='stock_view',entity_id=str(row.id),action='save',reason_code='STOCK_VIEW_SAVE')
    return view_dict(row)
