from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, BaseModel, GenericItem
from in_netsuite.base_models import Links, Link, GenericRef
from typing import Optional, Literal, Union
from in_netsuite.fields import Field, FieldQL, FieldRest
from datetime import date


class CreditMemoApplyElement(BaseModel):
    amount: Optional[float] = None
    apply: Optional[bool] = None
    doc: Optional[Union[str,dict]] = None
    line: Optional[int] = None


class CreditMemoApplyCollection(NetSuiteCollection):
    items: Optional[list[CreditMemoApplyElement]] = Field(None)


class CreditMemoItem(NetSuiteItem):
    item: Optional[Union[GenericItem, str]] = None
    account: Optional[Union[GenericItem, str]] = None
    amount: Optional[float] = None
    class_: Optional[Union[GenericItem, str]] = Field(None, alias="class")
    department: Optional[Union[GenericItem, str]] = None
    description: Optional[str] = None
    line: Optional[int] = None
    rate: Optional[float] = None


class CreditMemoItemCollection(NetSuiteCollection):
    items: Optional[list[Union[Links, CreditMemoItem]]] = Field(None)

    class Settings:
        item = CreditMemoItem


class CreditMemo(NetSuiteItem):
    id: Optional[str] = None
    account: Optional[Union[str, GenericRef]] = None
    amount_paid: Optional[float] = FieldRest(None, alias="amountPaid")
    apply: Optional[CreditMemoApplyCollection] = FieldRest(None)
    class_: Optional[str] = FieldRest(None, alias="class")
    entity: Optional[Union[GenericItem, str]] = None
    subsidiary: Optional[Union[GenericItem, str]] = None
    links: Optional[list[Link]] = FieldRest(None)
    item: Optional[Union[GenericItem, CreditMemoItemCollection]] = FieldRest(None)
    memo: Optional[str] = None
    transaction_id: Optional[str] = Field(None, alias="tranId")
    transaction_date: Optional[Union[str, date]] = Field(None, alias="tranDate")
    location: Optional[Union[GenericItem, str]] = None
    terms: Optional[Union[GenericItem, str]] = None
    subtotal: Optional[float] = FieldRest(None)
    record_type: Literal["creditmemo"] = FieldQL("invoice", alias="recordType")

    class Settings:
        table = "transaction"


class CreditMemoCollection(NetSuiteCollection):
    items: Optional[list[CreditMemo]] = Field(None)
