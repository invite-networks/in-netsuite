from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from in_netsuite.base_models import Link, Links, GenericRef
from typing import Optional, Literal, Union
from in_netsuite.fields import Field, FieldQL, FieldRest
from datetime import date


class InvoiceItem(NetSuiteItem):
    item: Optional[Union[GenericItem, str]] = None
    account: Optional[Union[GenericItem, str]] = None
    amount: Optional[float] = None
    class_: Optional[Union[GenericItem, str]] = Field(None, alias="class")
    department: Optional[Union[GenericItem, str]] = None
    description: Optional[str] = None
    line: Optional[int] = None
    rate: Optional[float] = None


class InvoiceItemCollection(NetSuiteCollection):
    items: Optional[list[Union[Links, InvoiceItem]]] = Field(None)


class Invoice(NetSuiteItem):
    id: Optional[str] = None
    memo: Optional[str] = None
    transaction_id: Optional[str] = Field(None, alias="tranId")
    transaction_date: Optional[Union[str, date]] = Field(None, alias="tranDate")
    account: Optional[Union[str, GenericRef]] = FieldRest(None)
    amount_paid: Optional[float] = Field(None, alias="amountPaid", json_schema_extra={"alias_ql": "foreignAmountPaid"})
    amount_remaining: Optional[float] = Field(
        None, alias="amountRemaining", json_schema_extra={"alias_ql": "foreignAmountUnpaid"}
    )
    class_: Optional[Union[str, GenericItem]] = FieldRest(None, alias="class")
    entity: Optional[Union[str, GenericItem]] = Field(None)
    employee: Optional[str] = FieldQL(None)
    created_from: Optional[GenericItem] = FieldRest(None, alias="createdFrom")
    links: Optional[list[Link]] = FieldRest(None)
    subsidiary: Optional[Union[str, GenericItem]] = FieldRest(None)
    item: Optional[Union[Links, InvoiceItemCollection]] = FieldRest(None)
    location: Optional[Union[GenericItem, str]] = FieldRest(None)
    terms: Optional[Union[GenericItem, str]] = FieldRest(None)
    subtotal: Optional[float] = FieldRest(None)
    record_type: Literal["invoice"] = FieldQL("invoice", alias="recordType")

    class Settings:
        table = "transaction"


class InvoiceCollection(NetSuiteCollection):
    items: Optional[list[Invoice]] = Field(None)
