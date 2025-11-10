from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem, GenericItem
from typing import Optional
from typing import Union
from in_netsuite.fields import Field


class Employee(NetSuiteItem):
    id: Optional[str] = None
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    email: Optional[str] = None
    location: Optional[Union[GenericItem, str]] = None


class EmployeeCollection(NetSuiteCollection):
    items: Optional[list[Employee]] = Field(None)
