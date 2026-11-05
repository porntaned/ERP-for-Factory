"""M5.4 (Issue #85): one LAMP-A19 production order end to end, through the real commands.

Runs seed_demo first (unchanged, so the M4.7 walkthrough still starts from L-0001 = 100 at RM-A),
then: chip Lots L-0002 30 and L-0003 20 and DRIVER Lot D-0001 20 received and RELEASED at RM-A;
order 10 x LAMP-A19 issues, consumes (a mistaken consumption is reversed), scraps, outputs
LAMP-0001 5 and LAMP-0002 4 (LAMP-0003 1 reversed), returns the rest and closes short with a
reason. Every command uses a fixed request UUID, so a rerun replays and posts nothing new.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from access_control.models import WarehouseRoleAssignment
from catalog.models import Item
from facilities.models import Warehouse
from inventory.models import Lot
from inventory.services import receive_stock
from manufacturing import services as mf
from manufacturing.models import BillOfMaterials
from quality.services import get_lot_disposition, transition_lot_disposition

from .seed_demo import demo_key

D = Decimal
SHORTFALL = "One lamp failed end-of-line test"


class Command(BaseCommand):
    help = (
        "Seed the M5.4 production demo (runs seed_demo first): one LAMP-A19 order from issue to "
        "a short close. Rerunnable; --reset FLUSHES the whole database first."
    )

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Flush ALL data first.")

    def handle(self, *args, reset=False, **options):
        call_command("seed_demo", reset=reset, verbosity=0)
        with transaction.atomic():
            summary = self.seed()
        self.stdout.write(self.style.SUCCESS(summary))

    def seed(self):
        users = {
            u.username: u for u in get_user_model().objects.filter(username__startswith="demo-")
        }
        wh = {w.code: w for w in Warehouse.objects.filter(plant__code="P1")}
        items = {i.code: i for i in Item.objects.filter(organization__code="LEDCO")}
        production, approver = users["demo-production"], users["demo-approver"]
        for code in ("LINE-1", "FG"):
            WarehouseRoleAssignment.objects.get_or_create(
                user=approver, warehouse=wh[code], role="APPROVER"
            )

        def stock(item, code, quantity):
            lot, _ = Lot.objects.get_or_create(item=items[item], code=code)
            receive_stock(
                lot=lot,
                warehouse=wh["RM-A"],
                actor=users["demo-warehouse"],
                quantity=D(quantity),
                reason="Synthetic demo delivery",
                request_id=demo_key(f"m54-receipt-{code}"),
            )
            if get_lot_disposition(lot=lot, warehouse=wh["RM-A"]) == "HOLD":
                transition_lot_disposition(
                    lot=lot,
                    warehouse=wh["RM-A"],
                    actor=users["demo-quality"],
                    expected_disposition="HOLD",
                    target_disposition="RELEASED",
                    reason="Synthetic demo incoming release",
                    request_id=demo_key(f"m54-release-{code}"),
                )
            return lot

        chip2, chip3, driver = (
            stock("LED-CHIP", "L-0002", "30"),
            stock("LED-CHIP", "L-0003", "20"),
            stock("DRIVER", "D-0001", "20"),
        )
        order = mf.create_production_order(
            bom=BillOfMaterials.objects.get(item=items["LAMP-A19"], status="ACTIVE"),
            quantity=D("10"),
            line_warehouse=wh["LINE-1"],
            output_warehouse=wh["FG"],
            actor=production,
            request_id=demo_key("m54-order"),
        )

        def step(name, command, **kwargs):
            return command(order=order, request_id=demo_key(f"m54-{name}"), **kwargs)

        line = dict(actor=production)
        for lot, quantity in ((chip2, "30"), (chip3, "10"), (driver, "10")):
            step(
                f"issue-{lot.code}",
                mf.issue_material,
                lot=lot,
                source_warehouse=wh["RM-A"],
                quantity=D(quantity),
                reason="Issue to line 1",
                **line,
            )
        for lot, quantity in ((chip2, "28"), (chip3, "8"), (driver, "9")):
            step(
                f"consume-{lot.code}",
                mf.consume_material,
                lot=lot,
                quantity=D(quantity),
                reason="Assembly run",
                **line,
            )
        mistake = step(
            "consume-mistake",
            mf.consume_material,
            lot=chip3,
            quantity=D("2"),
            reason="Assembly run (keyed twice)",
            **line,
        )
        step(
            "scrap-L-0002",
            mf.scrap_material,
            lot=chip2,
            quantity=D("2"),
            actor=approver,
            reason="Chips cracked during placement",
        )
        for code, quantity in (("LAMP-0001", "5"), ("LAMP-0002", "4")):
            step(
                f"output-{code}",
                mf.record_output,
                lot_code=code,
                quantity=D(quantity),
                reason="End-of-line output",
                **line,
            )
        failed = step(
            "output-LAMP-0003",
            mf.record_output,
            lot_code="LAMP-0003",
            quantity=D("1"),
            reason="End-of-line output",
            **line,
        )
        for name, posting, reason in (
            ("reverse-mistake", mistake, "Consumption keyed twice"),
            ("reverse-LAMP-0003", failed, "Lamp failed end-of-line test; not output"),
        ):
            mf.reverse_order_posting(
                order_posting=posting,
                actor=approver,
                reason=reason,
                request_id=demo_key(f"m54-{name}"),
            )
        for lot, quantity in ((chip3, "2"), (driver, "1")):
            step(
                f"return-{lot.code}",
                mf.return_material,
                lot=lot,
                destination_warehouse=wh["RM-A"],
                quantity=D(quantity),
                reason="Unused on line 1",
                **line,
            )
        order = step(
            "close", mf.close_production_order, actor=production, shortfall_reason=SHORTFALL
        )
        return (
            f"Seeded M5.4 production demo: order {order.pk} LAMP-A19 x 10 {order.status}, "
            "net output 9 (LAMP-0001 5, LAMP-0002 4 at FG, HOLD); shortfall reason recorded."
        )
