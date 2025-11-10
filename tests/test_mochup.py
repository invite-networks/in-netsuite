from dotenv import load_dotenv
import os
import pytest
import logging

from build.lib.in_netsuite.models.credit_memo import CreditMemoApplyCollection
from in_netsuite import NetSuite
from in_netsuite.restlets import RestLet
from in_netsuite.models import (
    Invoice, CustomerPayment, CreditMemoCollection, CreditMemo, CreditMemoItemCollection, CreditMemoApplyElement, CreditMemoApplyCollection
)
from in_netsuite.fields import FieldRest
from typing import Optional

pytest_plugins = ("pytest_asyncio",)


class TestNetSuite:
    def __getattr__(self, item):
        value = os.getenv(item) or os.getenv(item.upper())

        return value or Exception(f"{item} not defined in environment")

    def setup_method(self):
        load_dotenv()

        class CustomInvoice(Invoice):
            sent_to_customer: Optional[bool] = FieldRest(None, alias="custbodyinvitestcinvoice")

        NetSuite.init(
            self.account_id,
            self.client_id,
            self.client_secret,
            self.token_id,
            self.token_secret,
            custom_models={"invoice": CustomInvoice},
            restlets=[
                RestLet(
                    name="PaidInvoices",
                    id=1409,
                    required_kwargs={
                        "month": int,
                        "year": int,
                    },
                )
            ],
        )

        # Set logging based on the pyproject.toml but only for our loggers
        for logger in logging.root.manager.loggerDict:
            if logger.startswith("in_"):
                logging.getLogger(logger).setLevel(logging.getLogger().level)

        logging.getLogger().setLevel(logging.WARNING)

        self.ns = NetSuite()

    def teardown_method(self): ...

    @pytest.mark.asyncio
    async def test_method(self):
        import json
        #payment = CustomerPayment(payment=0)
        #response = await self.ns.customer_payment.transform('4972', payment)
        #print(response)

        #response = await self.ns.customer_payment.follow("https://8994692-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/customerpayment/74811/credit")
        #print (response.text)

        #response = await self.ns.customer_payment.find().all()
        #for line in response.items:
        #    print(line)

        #response = await self.ns.journal_entry.get("74508")
        #response = await self.ns.journal_entry.follow("https://8994692-sb1.suitetalk.api.netsuite.com/services/rest/record/v1/journalentry/74908/line")
        #for index, line in enumerate(response.json()["items"]):
        #    line_r = await self.ns.journal_entry.follow(line["links"][0]["href"])
        #    print(json.dumps(line_r.json(), indent=2))
        #    if index > 3:
        #        break


        #apply_items = [
        #    CreditMemoApplyElement(amount=38868.56, apply=True, doc="74611"),
        #    CreditMemoApplyElement(amount=1500.00, apply=True, doc="74611"),
        #]

        credit_items = [
            CreditMemoApplyElement(amount=38868.56, apply=True, doc="74908", line=3),
            CreditMemoApplyElement(amount=1500.00, apply=True, doc="74908", line=4),
        ]

        apply_items = [
            CreditMemoApplyElement(amount=40368.56, apply=True, doc="74611"),
        ]

        #credit_items = [
        #    CreditMemoApplyElement(amount=40368.56, apply=True, doc="74508"),
        #]

        await self.ns.customer_payment.create(
            CustomerPayment(
                customer='4972',
                apply=CreditMemoApplyCollection(
                    items=apply_items,
                ),
                credit=CreditMemoApplyCollection(
                    items=credit_items,
                ),
                transaction_date='2025-09-30'
            ),
            async_=False,
        )


        # for invoice in response.items:
        #    if not invoice.transaction_id.startswith("R"):
        #        print((await self.ns.invoice.get(id_=invoice.id, extra="allow")).prettyprint())

