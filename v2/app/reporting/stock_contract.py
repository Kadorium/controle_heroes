"""Stock query v1. Presentation never changes the selected population."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class StockQuery(BaseModel):
    q:str=Field(default="",max_length=200)
    modality_ids:list[str]=Field(default_factory=list,max_length=100)
    item_kind_ids:list[str]=Field(default_factory=list,max_length=100)
    model_ids:list[str]=Field(default_factory=list,max_length=100)
    location_ids:list[int]=Field(default_factory=list,max_length=100)
    position_ids:list[Literal['DOMESTIC','BONDED','QUARANTINE']]=Field(default_factory=lambda:['DOMESTIC'])
    product_id:int|None=None
    status:Literal['positive','all','zero']='positive'
    group_by:list[Literal['item_kind','model','modality']]=Field(default_factory=list,max_length=2)
    measures:list[Literal['quantity','cost','sale','margin']]=Field(default_factory=lambda:['quantity','cost','sale','margin'])
    composition_measure:Literal['quantity','cost','sale','margin']='cost'
    composition_open:bool=False
    secondary_open:bool=False
    visible_filters:list[Literal['modality_ids','item_kind_ids','model_ids','position_ids','location_ids']]=Field(default_factory=lambda:['modality_ids','item_kind_ids'])
    columns:list[Literal['quantity','unit_cost','cost','price','sale','margin']]=Field(default_factory=lambda:['quantity','unit_cost','cost','price','sale','margin'])
    sort:Literal['name','-name','quantity','-quantity','cost','-cost','sale','-sale']='name'
    price_list_id:int|None=None
    limit:int=Field(default=25,ge=1,le=100)
    offset:int=Field(default=0,ge=0)
    @model_validator(mode='before')
    @classmethod
    def explicit_empty_filters(cls, values):
        if isinstance(values, dict):
            values=dict(values)
            for key in ['modality_ids','item_kind_ids','model_ids','position_ids','location_ids','group_by']:
                if isinstance(values.get(key),list):values[key]=[v for v in values[key] if v != '']
        return values
    @model_validator(mode='after')
    def unique(self):
        for key in ['modality_ids','item_kind_ids','model_ids','location_ids','position_ids','group_by','measures','visible_filters','columns']:
            setattr(self,key,list(dict.fromkeys(getattr(self,key))))
        if not self.measures:raise ValueError('Escolha ao menos uma medida')
        return self
