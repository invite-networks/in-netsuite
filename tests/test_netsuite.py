from dotenv import load_dotenv
import os
import pytest
import logging
from tests.test_data import get_invoice_data, get_invoice_update_data
from in_netsuite import NetSuite
from in_netsuite.exceptions import DoesNotExistError, NetSuiteDataChangedError
from in_netsuite.models import (
    Employee,
    Vendor,
    Department,
    Invoice,
    NetSuiteCollection,
    Customer,
    Links,
)
from in_netsuite.operators import And, Or
from in_netsuite.fields import FieldRest
from typing import Optional


pytest_plugins = ("pytest_asyncio",)


class TestNetSuite:
    def __getattr__(self, item):
        value = os.getenv(item) or os.getenv(item.upper())

        if not value:
            raise ValueError(f"{item} not defined in environment")
        return value

    def get_logging_level(self, module):
        prefix = "TEST_LOGGING_LEVEL"
        try:
            level = self.__getattr__(f"{prefix}_{module}".upper())
        except ValueError:
            if module.startswith("in_"):
                level = self.__getattr__("TEST_LOGGING_LEVEL")
            else:
                level = "WARNING"
        return level

    def setup_method(self):
        load_dotenv()

        # Set logging based on the pyproject.toml but only for our loggers
        for logger in logging.root.manager.loggerDict:
            logging.getLogger(logger).setLevel(self.get_logging_level(logger))

        logging.getLogger().setLevel(self.get_logging_level("root"))

        class CustomInvoice(Invoice):
            sent_to_customer: Optional[bool] = FieldRest(None, alias="custbodyinvitestcinvoice")

        NetSuite.init(
            self.account_id,
            self.client_id,
            self.client_secret,
            self.token_id,
            self.token_secret,
            custom_models={"invoice": CustomInvoice},
        )

        self.ns = NetSuite()

    def teardown_method(self): ...

    @pytest.mark.asyncio
    async def test_cache(self):
        await self.ns.customer.get(id_=self.test_customer_id)
        await self.ns.customer.get(id_=self.test_customer_id)
        response = await self.ns.customer.get(id_=self.test_customer_id)
        cache_info = self.ns.customer.get.cache_info()

        assert response.__class__.__name__ == "CustomerRest"
        assert cache_info.hits == 2
        assert cache_info.misses == 1

    @pytest.mark.asyncio
    async def test_invoice_create(self):
        # Create a job
        job = await self.ns.invoice.create(get_invoice_data(), async_=True, poll=False)

        # Create a second invoice using polling
        response = await self.ns.invoice.create(get_invoice_data(), async_=True, poll=True)
        await response.delete()

        # Poll the first job
        response = await job.poll()
        await response.delete()

    @pytest.mark.asyncio
    async def test_invoice_select(self):
        invoice_data = get_invoice_data()
        invoice = await self.ns.invoice.create(invoice_data, async_=True, poll=True)

        response = (
            await self.ns.invoice.select(Invoice.id, Invoice.memo, Invoice.transaction_date)
            .where(And(Invoice.record_type == "invoice", Invoice.memo == invoice_data.memo))
            .all()
        )

        await invoice.delete()

        assert len(response.items) >= 1
        assert type(response.items[0].id) is str
        assert type(response.items[0].memo) is str
        assert type(response.items[0].transaction_date) is str

    @pytest.mark.asyncio
    async def test_customer_get_one(self):
        response = await self.ns.customer.get(id_=self.test_customer_id)

        assert response.__class__.__name__ == "CustomerRest"

        with pytest.raises(DoesNotExistError):
            await self.ns.customer.get(id_="9999999")

    @pytest.mark.asyncio
    async def test_customer_select_star(self):
        response = await self.ns.customer.select().all(extra="allow")

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert type(response.items[0].id) is str
        assert type(response.items[0].company_name) is str
        assert type(response.items[0].sales_rep) is str

    @pytest.mark.asyncio
    async def test_customer_select(self):
        response = await self.ns.customer.select().all()

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert type(response.items[0].company_name) is str
        with pytest.raises(AttributeError):
            _ = response.items[0].url

    @pytest.mark.asyncio
    async def test_customer_columns(self):
        response = await self.ns.customer.select(Customer.id).all()

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert type(response.items[0].id) is str
        with pytest.raises(AttributeError):
            _ = response.items[0].company_name

    @pytest.mark.asyncio
    async def test_customer_where(self):
        response = await self.ns.customer.select().where(Customer.id == self.test_customer_id).all()

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert len(response.items) == 1
        assert response.items[0].company_name == self.test_customer_name

    @pytest.mark.asyncio
    async def test_customer_join_where(self):
        response = (
            await self.ns.customer.select()
            .join(Customer.sales_rep == Employee.id)
            .where(Customer.id == self.test_customer_id)
            .all()
        )

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert len(response.items) == 1
        assert response.items[0].sales_rep.first_name == "Test"

    @pytest.mark.asyncio
    async def test_customer_columns_join_where(self):
        response = (
            await self.ns.customer.select(Employee.first_name)
            .join(Customer.sales_rep == Employee.id)
            .where(Customer.id == self.test_customer_id, Employee.first_name == "Test")
            .all()
        )

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert len(response.items) == 1
        assert response.items[0].sales_rep.first_name == "Test"
        assert len(response.items[0].sales_rep) == 1
        with pytest.raises(AttributeError):
            _ = response.items[0].sales_rep.last_name

    @pytest.mark.asyncio
    async def test_customer_join_where_operator(self):
        response = (
            await self.ns.customer.select()
            .join(Customer.sales_rep == Employee.id)
            .where(Or(Customer.id == self.test_customer_id, Employee.first_name == "Test"))
            .all()
        )

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert response.total_results > 1

    @pytest.mark.asyncio
    async def test_customer_join_where_nested_operator(self):
        response = (
            await self.ns.customer.select()
            .join(Customer.sales_rep == Employee.id)
            .where(
                And(
                    Or(Customer.id == self.test_customer_id, Customer.id == self.test_customer_id),
                    Employee.first_name == "Test",
                )
            )
            .all()
        )

        assert response.response.__class__.__name__ == "CustomerCollectionQL"
        assert response.total_results == 1

    @pytest.mark.asyncio
    async def test_invoice_get(self):
        response = await self.ns.invoice.get(self.test_invoice_id)

        assert response.__class__.__name__ == "CustomInvoiceRest"
        assert response.id == self.test_invoice_id
        assert type(response.item) is Links
        with pytest.raises(AttributeError):
            _ = response.record_type

    @pytest.mark.asyncio
    async def test_invoice_select_where(self):
        response = await self.ns.invoice.select().where(Invoice.id == self.test_invoice_id).all()

        assert response.response.__class__.__name__ == "InvoiceCollectionQL"
        assert response.items[0].id == self.test_invoice_id
        assert response.items[0].record_type == "invoice"
        with pytest.raises(AttributeError):
            _ = response.items[0].account

    @pytest.mark.asyncio
    async def test_vendor_find(self):
        response = await self.ns.vendor.find().all()

        assert type(response) is NetSuiteCollection

    @pytest.mark.asyncio
    async def test_vendor_get(self):
        response = await self.ns.vendor.get(id_=self.test_vendor_id)

        assert response.__class__.__name__ == "VendorRest"

    @pytest.mark.asyncio
    async def test_vendor_select_by_model_join(self):
        response = (
            await self.ns.vendor.select(Vendor, Department)
            .join(Vendor.department == Department.id)
            .where(Vendor.id == self.test_vendor_id)
            .all()
        )

        assert response.__class__.__name__ == "SuiteQLResponse"
        assert response.items[0].id == self.test_vendor_id
        assert type(response.items[0].company_name) is str
        assert response.items[0].department.id is None

    @pytest.mark.asyncio
    async def test_invoice_update(self):
        invoice_data = get_invoice_data()
        response = await self.ns.invoice.create(invoice_data)
        invoice_id = response.id

        invoice_data.item = get_invoice_update_data()
        try:
            response = await response.update(invoice_data)

        except NetSuiteDataChangedError:
            print("We are going to refresh and try again")
            # Run a get request to refresh and try it again
            response = await self.ns.invoice.get(invoice_id)
            response = await response.update(invoice_data)

        await response.delete()
