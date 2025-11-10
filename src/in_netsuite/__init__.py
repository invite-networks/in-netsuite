from in_netsuite.rest import RestRequests
from in_netsuite.exceptions import NetSuiteNotInitializedError
from in_netsuite.restlets import RestLet
from in_netsuite.netsuite import (
    NetSuiteItem,
    NetSuiteCollection,
    NetSuiteJob,
    _QLInstance,
    _RestInstance,
    _Instance,
)
from in_netsuite.models import (
    CreditMemoApplyCollection,
    CreditMemoApplyElement,
    CreditMemoCollection,
    CreditMemo,
    CreditMemoItemCollection,
    CreditMemoItem,
    CustomerCollection,
    Customer,
    CustomerPaymentCollection,
    CustomerPayment,
    DepartmentCollection,
    Department,
    EmployeeCollection,
    Employee,
    InvoiceCollection,
    Invoice,
    InvoiceItemCollection,
    InvoiceItem,
    JournalLineCollection,
    JournalLine,
    JournalEntry,
    SalesOrderCollection,
    SalesOrder,
    VendorCollection,
    Vendor,
    JournalEntryCollection,
)
from typing import Optional, Iterable
import logging

__all__ = [
    "NetSuite",
    "NetSuiteItem",
    "NetSuiteCollection",
    "NetSuiteJob",
    "CreditMemoApplyCollection",
    "CreditMemoApplyElement",
    "CreditMemoCollection",
    "CreditMemo",
    "CreditMemoItemCollection",
    "CreditMemoItem",
    "CustomerCollection",
    "Customer",
    "CustomerPaymentCollection",
    "CustomerPayment",
    "DepartmentCollection",
    "Department",
    "EmployeeCollection",
    "Employee",
    "InvoiceCollection",
    "Invoice",
    "InvoiceItemCollection",
    "InvoiceItem",
    "JournalLineCollection",
    "JournalLine",
    "JournalEntry",
    "VendorCollection",
    "Vendor",
    "RestRequests",
]

logger = logging.getLogger("in_netsuite_init")


class NetSuite:
    """
    Represents a NetSuite integration for managing and interacting with collections
    such as invoices, employees, and customers.

    This class provides the initialization and configuration mechanism required to
    connect to a NetSuite instance, as well as access to the underlying collections.
    The purpose of this class is to facilitate interactions with NetSuite’s API
    through the provided collections. The class requires explicit initialization
    before use, and provides an interface for accessing invoice, employee, and customer
    collections.

    Attributes:
        _initialized (bool): Tracks whether the NetSuite class has been initialized.
        account_id (Optional[str]): The account ID used for NetSuite authentication.
        client_id (Optional[str]): The consumer key used for NetSuite authentication.
        client_secret (Optional[str]): The consumer secret used for NetSuite authentication.
        token_id (Optional[str]): The token ID used for NetSuite authentication.
        token_secret (Optional[str]): The token secret used for NetSuite authentication.
        invoice: An instance of the InvoiceCollection for managing invoices.
        employee: An instance of the EmployeeCollection for managing employees.
        customer: An instance of the CustomerCollection for managing customers.

    Methods:
        init: Initializes the NetSuite class with necessary credentials and sets
        it up for RestRequests integration.
    """

    _initialized = False
    account_id: str
    realm: str
    client_id: str
    client_secret: str
    token_id: str
    token_secret: str
    _restlets: Optional[Iterable[RestLet]] = None
    credit_memo = _Instance(CreditMemoCollection)
    customer = _Instance(CustomerCollection)
    customer_payment = _Instance(CustomerPaymentCollection)
    department = _Instance(DepartmentCollection)
    employee = _Instance(EmployeeCollection)
    invoice = _Instance(InvoiceCollection)
    journal_entry = _Instance(JournalEntryCollection)
    sales_order = _Instance(SalesOrderCollection)
    vendor = _Instance(VendorCollection)

    def __init__(self):
        """
        Initialize the netsuite class
        Args:
        """

        if not self._initialized:
            raise NetSuiteNotInitializedError("NetSuite has not been initialized")

    @classmethod
    def init(
        cls,
        account_id: str,
        client_id: str,
        client_secret: str,
        token_id: str,
        token_secret: str,
        custom_models: Optional[dict[str, type[NetSuiteItem]]] = None,
        restlets: Optional[Iterable[RestLet]] = None,
    ):
        """
        Initialize the netsuite class
        Args:
            account_id: Account ID
            client_id: Consumer Key
            client_secret: Consumer Secret
            token_id: Token ID
            token_secret: Token Secret
            custom_models: Custom models to be used for the netsuite class
            restlets: Registered suitelets that can be called
        """

        cls.account_id = account_id.lower()
        cls.client_id = client_id
        cls.client_secret = client_secret
        cls.token_id = token_id
        cls.token_secret = token_secret

        if "-sb" in cls.account_id:
            cls.realm = cls.account_id.replace("-sb", "_SB")
        else:
            cls.realm = cls.account_id

        RestRequests.init(netsuite=cls)

        if custom_models is not None:
            for instance, model in custom_models.items():
                if not hasattr(cls, instance):
                    raise ValueError(f"Invalid instance name: {instance}")

                logger.debug(f"Applying custom model {model} to {instance} instance")
                setattr(getattr(cls, instance), "model", model)

        cls._restlets = restlets

        cls._initialized = True

    def restlet(self, name: str) -> RestLet:
        """
        Find a restlet by name and return it
        """

        if self._restlets is None:
            raise ValueError("There are no RestLets registered")

        restlets_ = next((suitelet_ for suitelet_ in self._restlets if suitelet_.name == name), None)

        if restlets_ is None:
            raise ValueError(f"RestLets {name} is not registered")

        return restlets_
