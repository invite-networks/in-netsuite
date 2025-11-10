from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem
from typing import Optional
from typing import Union
from in_netsuite.fields import Field


class Department(NetSuiteItem):
    id: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = Field(None, alias="fullName")


class DepartmentCollection(NetSuiteCollection):
    items: Optional[list[Department]] = Field(None)
    department: Optional[Union[Department, str]] = None
