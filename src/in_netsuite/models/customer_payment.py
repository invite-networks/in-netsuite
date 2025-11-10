from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from in_netsuite.models.credit_memo import CreditMemoApplyCollection
from typing import Optional, Literal
from typing import Union
from in_netsuite.fields import Field, FieldQL
from datetime import date


class CustomerPayment(NetSuiteItem):
    account: Optional[str] = None
    customer: Optional[Union[GenericItem, str]] = None
    payment: Optional[float] = None
    apply: Optional[CreditMemoApplyCollection] = None
    credit: Optional[CreditMemoApplyCollection] = None
    transaction_date: Optional[Union[str, date]] = Field(None, alias="tranDate")
    record_type: Literal["customerpayment"] = FieldQL("customerpayment", alias="recordType")

    class Settings:
        table = "transaction"


class CustomerPaymentCollection(NetSuiteCollection):
    items: Optional[list[Union[CustomerPayment, GenericItem]]] = Field(None)
