from in_netsuite.netsuite import NetSuiteCollection, NetSuiteItem
from in_netsuite.models.department import Department
from typing import Optional
from typing import Union
from in_netsuite.fields import Field


class Vendor(NetSuiteItem):
    id: Optional[str] = None
    company_name: Optional[str] = Field(None, alias="companyName")
    department: Optional[Union[Department, str]] = Field(None, alias="custentityinvdeptvendor")


class VendorCollection(NetSuiteCollection):
    items: Optional[list[Vendor]] = Field(None)
