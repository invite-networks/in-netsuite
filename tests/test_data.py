from in_netsuite.models import Invoice, InvoiceItem, InvoiceItemCollection
import random


def get_invoice_data():
    id_ = random.randint(1, 1000000)
    return Invoice(
        entity="3317",  # XYZ Demo
        subsidiary="1",
        memo="Test Invoice",
        transaction_id=f"R20250321C3317T{id_}",
        location="1",  # Utah
        item=InvoiceItemCollection(
            items=[
                InvoiceItem(
                    amount=1.0,
                    rate=1.0,
                    class_="4",  # Referral
                    department="16",  # Legacy Collaboration
                    description="Lumen",
                    item="22645",  # Referral
                ),
                InvoiceItem(
                    amount=1.0,
                    rate=1.0,
                    class_="4",  # Referral
                    department="3",  # Infrastructure
                    description="Comcast",
                    item="22645",  # Referral
                ),
            ]
        ),
    )


def get_invoice_update_data():
    return InvoiceItemCollection(
        items=[
            InvoiceItem(
                amount=1.5,
                rate=1.5,
                class_="4",  # Referral
                department="16",  # Legacy Collaboration
                description="Lumen",
                item="22645",  # Referral
            )
        ]
    )
