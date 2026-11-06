"""Create the synthetic pilot factory through the real Inventory and Quality commands.

Idempotent: master data uses get_or_create and every command uses a fixed request UUID,
so a rerun replays the same receipt and release instead of posting again.
"""

from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from access_control.models import WarehouseRoleAssignment
from catalog.models import Item, UnitOfMeasure
from facilities.models import Organization, Plant, Warehouse
from inventory.models import Lot
from inventory.services import receive_stock
from manufacturing.services import approve_bom, create_bom_draft
from quality.services import record_inspection


def demo_key(name):
    return uuid5(NAMESPACE_URL, f"erp-for-factory/demo/{name}")


class Command(BaseCommand):
    help = (
        "Seed synthetic demo data (LEDCO, plant P1, warehouses RM-A/RM-B/LINE-1/FG, BOM). "
        "--reset first FLUSHES the whole database; use only on a disposable database."
    )

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Flush ALL data first.")

    def handle(self, *args, reset=False, **options):
        if reset:
            call_command("flush", interactive=False, verbosity=0)
        with transaction.atomic():
            summary = self.seed()
        self.stdout.write(self.style.SUCCESS(summary))

    def seed(self):
        org, _ = Organization.objects.get_or_create(
            code="LEDCO", defaults={"display_name": "LED Assembly Co. (synthetic)"}
        )
        plant, _ = Plant.objects.get_or_create(
            organization=org, code="P1", defaults={"display_name": "Assembly plant 1"}
        )
        warehouses = {
            code: Warehouse.objects.get_or_create(
                plant=plant, code=code, defaults={"display_name": name}
            )[0]
            for code, name in (
                ("RM-A", "Raw material A"),
                ("RM-B", "Raw material B"),
                ("LINE-1", "Production line 1"),
                ("FG", "Finished goods"),
            )
        }
        each, _ = UnitOfMeasure.objects.get_or_create(code="EA", defaults={"display_name": "Each"})
        items = {
            code: Item.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"display_name": name, "item_type": kind, "base_uom": each},
            )[0]
            for code, name, kind in (
                ("LED-CHIP", "LED chip", "RAW"),
                ("DRIVER", "LED driver", "RAW"),
                ("LAMP-A19", "A19 LED lamp", "FINISHED"),
            )
        }
        lot, _ = Lot.objects.get_or_create(item=items["LED-CHIP"], code="L-0001")

        users = {}
        for username, role, codes in (
            ("demo-warehouse", "WAREHOUSE", ("RM-A", "RM-B")),
            ("demo-quality", "QUALITY", ("RM-A", "RM-B", "FG")),
            ("demo-approver", "APPROVER", ("RM-A", "RM-B", "FG")),
            ("demo-production", "PRODUCTION", ("RM-A", "RM-B", "LINE-1", "FG")),
        ):
            user, created = get_user_model().objects.get_or_create(username=username)
            if created:
                user.set_unusable_password()
                user.save()
            for code in codes:
                WarehouseRoleAssignment.objects.get_or_create(
                    user=user, warehouse=warehouses[code], role=role
                )
            users[role] = user

        receive_stock(
            lot=lot,
            warehouse=warehouses["RM-A"],
            actor=users["WAREHOUSE"],
            quantity=Decimal("100"),
            reason="Synthetic demo delivery",
            request_id=demo_key("receipt-1"),
        )
        # M6.1: an INCOMING inspection that passes releases the delivery.
        record_inspection(
            lot=lot,
            warehouse=warehouses["RM-A"],
            result="PASS",
            sample_quantity=Decimal("1"),
            note="Synthetic demo incoming inspection",
            actor=users["QUALITY"],
            request_id=demo_key("release-1"),
        )
        # M5.1: LAMP-A19 v1 = 4 LED-CHIP + 1 DRIVER, drafted by production, approved by approver.
        bom = create_bom_draft(
            item=items["LAMP-A19"],
            lines=[(items["LED-CHIP"], Decimal("4")), (items["DRIVER"], Decimal("1"))],
            actor=users["PRODUCTION"],
            request_id=demo_key("bom-lamp-a19-v1"),
        )
        approve_bom(
            bom=bom, actor=users["APPROVER"], request_id=demo_key("bom-lamp-a19-v1-approve")
        )
        return (
            "Seeded LEDCO/P1: RM-A, RM-B, LINE-1, FG; lot L-0001 received 100 at RM-A and RELEASED; "
            "BOM LAMP-A19 v1 ACTIVE."
        )
