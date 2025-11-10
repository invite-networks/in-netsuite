from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from in_netsuite.base_models import Link
from typing import Optional, Literal, Union
from in_netsuite.fields import Field, FieldQL

class JournalLine(NetSuiteItem):
    """
    https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2024.2/index.html#/definitions/statisticalJournalEntry-lineElement
    """

    account: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    credit: Optional[float] = None
    debit: Optional[float] = None
    department: Optional[str] = None
    entity: Optional[str] = None
    subsidiary: Optional[Union[GenericItem, str]] = None
    links: Optional[list[Link]] = None
    line: Optional[int] = None
    memo: Optional[str] = None


class JournalLineCollection(NetSuiteCollection):
    items: Optional[list[JournalLine]] = Field(None)


class JournalEntry(NetSuiteItem):
    id: Optional[str] = None
    memo: Optional[str] = None
    subsidiary: Optional[Union[GenericItem, str]] = None
    line: Optional[JournalLineCollection] = None
    transaction_date: Optional[str] = Field(None, alias="tranDate")
    record_type: Literal["journalentry"] = FieldQL("journalentry", alias="recordType")

    class Settings:
        table = "transaction"

class JournalEntryCollection(NetSuiteCollection):
    items: Optional[list[JournalEntry, GenericItem]] = Field(None)
