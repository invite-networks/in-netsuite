from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from in_netsuite.base_models import Links
from typing import Optional, Union
from in_netsuite.fields import Field


class SalesOrderItem(NetSuiteItem):
    item: Optional[Union[GenericItem, str]] = None


class SalesOrderItemCollection(NetSuiteCollection):
    items: Optional[list[Union[Links, SalesOrderItem]]] = Field(None)


class SalesOrder(NetSuiteItem):
    id: Optional[str] = None
    memo: Optional[str] = None
    item: Optional[Union[Links, SalesOrderItemCollection]] = Field(None)


class SalesOrderCollection(NetSuiteCollection):
    items: Optional[list[SalesOrder]] = Field(None)
