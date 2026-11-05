"""M5.2b (Issue #75): rules for consumption, scrap, output and closing, for every writer.

- An order posting is inserted only for an OPEN order (row locked FOR UPDATE).
- CONSUME / SCRAP: the entry is on the order line, its Lot item is a BOM component, and the
  order's holding of that Lot never goes negative.
- OUTPUT: the entry is at the order's output warehouse for the BOM item; total output never
  exceeds the order quantity; an output Lot belongs to one order and has no other history.
- Holding (issued - returned - consumed - scrapped) must be zero to cancel or close.
- OPEN -> CLOSED becomes a legal transition; its key registers as ORDER_CLOSE.
"""

import importlib

from django.db import migrations

RULES = importlib.import_module("manufacturing.migrations.0002_database_rules")
_ORDER_GUARD_START = RULES.FORWARD.index("CREATE FUNCTION manufacturing_guard_order()")
_ORDER_GUARD_END = RULES.FORWARD.index("$$;", _ORDER_GUARD_START) + 3
ORIGINAL_ORDER_GUARD = RULES.FORWARD[_ORDER_GUARD_START:_ORDER_GUARD_END].replace(
    "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1
)
CLOSING_ORDER_GUARD = ORIGINAL_ORDER_GUARD.replace(
    "IF OLD.status = 'OPEN' AND NEW.status = 'CANCELLED' THEN",
    "IF OLD.status = 'OPEN' AND NEW.status IN ('CANCELLED', 'CLOSED') THEN",
).replace("moves only OPEN -> CANCELLED", "moves only OPEN -> CANCELLED or CLOSED")
assert CLOSING_ORDER_GUARD != ORIGINAL_ORDER_GUARD
MOVEMENTS = importlib.import_module("manufacturing.migrations.0004_material_movement_rules")
_CANCEL_START = MOVEMENTS.FORWARD.index(
    "CREATE FUNCTION manufacturing_guard_order_cancel_holding()"
)
_CANCEL_END = MOVEMENTS.FORWARD.index("$$;", _CANCEL_START) + 3
MOVEMENT_CANCEL_GUARD = (
    MOVEMENTS.FORWARD[_CANCEL_START:_CANCEL_END].replace(
        "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1
    )
    + "\n"
)

FORWARD = (
    r"""
ALTER TABLE manufacturing_orderposting ALTER COLUMN id SET GENERATED ALWAYS;

CREATE OR REPLACE FUNCTION manufacturing_order_lot_holding(order_id bigint, lot_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE((
        SELECT SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END)
        FROM manufacturing_productionmaterialmovement m
        JOIN inventory_stocktransfer t ON t.id = m.transfer_id
        JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
        WHERE m.order_id = $1 AND d.lot_id = $2), 0)
    + COALESCE((
        SELECT SUM(e.quantity_delta)
        FROM manufacturing_orderposting op
        JOIN inventory_productionposting p ON p.id = op.posting_id
        JOIN inventory_stockledgerentry e ON e.id = p.ledger_entry_id
        WHERE op.order_id = $1 AND op.kind IN ('CONSUME', 'SCRAP') AND e.lot_id = $2), 0);
$$;

CREATE FUNCTION manufacturing_order_holds_material(order_id bigint)
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM (
            SELECT d.lot_id FROM manufacturing_productionmaterialmovement m
            JOIN inventory_stocktransfer t ON t.id = m.transfer_id
            JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
            WHERE m.order_id = $1
        ) lots
        WHERE manufacturing_order_lot_holding($1, lots.lot_id) <> 0
    );
$$;

CREATE OR REPLACE FUNCTION manufacturing_guard_order_cancel_holding()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'OPEN' AND NEW.status IN ('CANCELLED', 'CLOSED')
       AND manufacturing_order_holds_material(NEW.id) THEN
        RAISE EXCEPTION 'an order holding material on its line cannot be cancelled or closed'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_order_zz_close_key
BEFORE UPDATE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_register_request_key('ORDER_CLOSE', 'close_request_id');

CREATE FUNCTION manufacturing_guard_order_posting()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    o record;
    e record;
    bom_item bigint;
    total numeric;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'order postings are immutable' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO o FROM manufacturing_productionorder WHERE id = NEW.order_id FOR UPDATE;
    IF o.status IS DISTINCT FROM 'OPEN' THEN
        RAISE EXCEPTION 'postings are only for an OPEN order' USING ERRCODE = '23514';
    END IF;
    SELECT p.kind, l.lot_id, l.warehouse_id, l.quantity_delta, lot.item_id INTO e
    FROM inventory_productionposting p
    JOIN inventory_stockledgerentry l ON l.id = p.ledger_entry_id
    JOIN inventory_lot lot ON lot.id = l.lot_id
    WHERE p.id = NEW.posting_id;
    IF e.kind IS DISTINCT FROM NEW.kind THEN
        RAISE EXCEPTION 'the order posting kind must match the Inventory posting' USING ERRCODE = '23514';
    END IF;
    IF NEW.kind IN ('CONSUME', 'SCRAP') THEN
        IF e.warehouse_id <> o.line_warehouse_id OR NOT EXISTS (
            SELECT 1 FROM manufacturing_bomline WHERE bom_id = o.bom_id AND component_id = e.item_id
        ) THEN
            RAISE EXCEPTION 'consumption and scrap are of BOM components on the order line'
                USING ERRCODE = '23514';
        END IF;
        IF manufacturing_order_lot_holding(o.id, e.lot_id) + e.quantity_delta < 0 THEN
            RAISE EXCEPTION 'the order does not hold that much of this Lot' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT item_id INTO bom_item FROM manufacturing_billofmaterials WHERE id = o.bom_id;
    IF e.warehouse_id <> o.output_warehouse_id OR e.item_id <> bom_item THEN
        RAISE EXCEPTION 'output is the BOM item at the order output warehouse' USING ERRCODE = '23514';
    END IF;
    SELECT COALESCE(SUM(l.quantity_delta), 0) INTO total
    FROM manufacturing_orderposting op
    JOIN inventory_productionposting p ON p.id = op.posting_id
    JOIN inventory_stockledgerentry l ON l.id = p.ledger_entry_id
    WHERE op.order_id = o.id AND op.kind = 'OUTPUT';
    IF total + e.quantity_delta > o.quantity THEN
        RAISE EXCEPTION 'output exceeds the order quantity' USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM inventory_stockledgerentry l
        WHERE l.lot_id = e.lot_id AND NOT EXISTS (
            SELECT 1 FROM inventory_productionposting p
            JOIN manufacturing_orderposting op ON op.posting_id = p.id
            WHERE p.ledger_entry_id = l.id AND op.order_id = o.id AND op.kind = 'OUTPUT'
        ) AND l.id <> (SELECT ledger_entry_id FROM inventory_productionposting WHERE id = NEW.posting_id)
    ) THEN
        RAISE EXCEPTION 'an output Lot belongs to one order and has no other history'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_order_posting_guard
BEFORE INSERT OR UPDATE OR DELETE ON manufacturing_orderposting FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_order_posting();
"""
    + CLOSING_ORDER_GUARD
)

REVERSE = (
    r"""
DROP TRIGGER manufacturing_order_posting_guard ON manufacturing_orderposting;
DROP FUNCTION manufacturing_guard_order_posting();
DROP TRIGGER manufacturing_order_zz_close_key ON manufacturing_productionorder;
"""
    + MOVEMENT_CANCEL_GUARD
    + r"""
DROP FUNCTION manufacturing_order_holds_material(bigint);
CREATE OR REPLACE FUNCTION manufacturing_order_lot_holding(order_id bigint, lot_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE(SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END), 0)
    FROM manufacturing_productionmaterialmovement m
    JOIN inventory_stocktransfer t ON t.id = m.transfer_id
    JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
    WHERE m.order_id = $1 AND d.lot_id = $2;
$$;
ALTER TABLE manufacturing_orderposting ALTER COLUMN id SET GENERATED BY DEFAULT;
"""
    + ORIGINAL_ORDER_GUARD
)


class Migration(migrations.Migration):
    dependencies = [
        ("manufacturing", "0005_order_postings_and_close"),
        ("inventory", "0012_production_posting_rules"),
    ]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
