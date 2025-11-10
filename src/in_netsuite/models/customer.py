from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from in_netsuite.models.employee import Employee
from typing import Optional
from typing import Union
from in_netsuite.fields import Field


class Customer(NetSuiteItem):
    id: Optional[str] = None
    company_name: Optional[str] = Field(None, alias="companyName")
    sales_rep: Optional[Union[Employee, str]] = Field(None, alias="salesRep")


class CustomerCollection(NetSuiteCollection):
    items: Optional[list[Union[Customer, GenericItem]]] = Field(None)
