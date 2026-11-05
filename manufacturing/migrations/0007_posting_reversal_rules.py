"""M5.2c (Issue #81): manufacturing rules for production posting reversals.

- A reversal is inserted only while the posting's order is OPEN (order row locked FOR UPDATE).
- Holding of a Lot adds reversed consumption and scrap back.
- Net output = OUTPUT - reversed OUTPUT; the output cap uses it.
- An output Lot may also hold reversal entries of the same order's outputs.
"""

import importlib

from django.db import migrations

POSTINGS = importlib.import_module("manufacturing.migrations.0006_order_posting_rules")


def _function(sql, name):
    start = sql.index(f"FUNCTION {name}(")
    start = sql.rindex("CREATE", 0, start)
    end = sql.index("$$;", sql.index("$$", sql.index("AS $$", start) + 5)) + 3
    return sql[start:end].replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1) + "\n"


OLD_HOLDING = _function(POSTINGS.FORWARD, "manufacturing_order_lot_holding")
OLD_GUARD = _function(POSTINGS.FORWARD, "manufacturing_guard_order_posting")

OLD_TOTAL = """    SELECT COALESCE(SUM(l.quantity_delta), 0) INTO total
    FROM manufacturing_orderposting op
    JOIN inventory_productionposting p ON p.id = op.posting_id
    JOIN inventory_stockledgerentry l ON l.id = p.ledger_entry_id
    WHERE op.order_id = o.id AND op.kind = 'OUTPUT';"""
OLD_OWNER = """            WHERE p.ledger_entry_id = l.id AND op.order_id = o.id AND op.kind = 'OUTPUT'
        ) AND l.id"""
NEW_OWNER = """            WHERE p.ledger_entry_id = l.id AND op.order_id = o.id AND op.kind = 'OUTPUT'
        ) AND NOT EXISTS (
            SELECT 1 FROM inventory_productionpostingreversal r
            JOIN manufacturing_orderposting op ON op.posting_id = r.posting_id
            WHERE r.ledger_entry_id = l.id AND op.order_id = o.id AND op.kind = 'OUTPUT'
        ) AND l.id"""
assert OLD_TOTAL in OLD_GUARD and OLD_OWNER in OLD_GUARD
NEW_GUARD = OLD_GUARD.replace(
    OLD_TOTAL, "    total := manufacturing_order_net_output(o.id);"
).replace(OLD_OWNER, NEW_OWNER)

FORWARD = (
    r"""
CREATE FUNCTION manufacturing_order_posting_total(order_id bigint, kinds text[], lot_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    -- Signed entries of the order's postings of these kinds, plus their reversals;
    -- lot_id NULL means every Lot.
    SELECT COALESCE(SUM(e.quantity_delta), 0) + COALESCE(SUM(re.quantity_delta), 0)
    FROM manufacturing_orderposting op
    JOIN inventory_productionposting p ON p.id = op.posting_id
    JOIN inventory_stockledgerentry e ON e.id = p.ledger_entry_id
    LEFT JOIN inventory_productionpostingreversal r ON r.posting_id = p.id
    LEFT JOIN inventory_stockledgerentry re ON re.id = r.ledger_entry_id
    WHERE op.order_id = $1 AND op.kind = ANY($2) AND ($3 IS NULL OR e.lot_id = $3);
$$;

CREATE FUNCTION manufacturing_order_net_output(order_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT manufacturing_order_posting_total($1, ARRAY['OUTPUT'], NULL);
$$;

CREATE OR REPLACE FUNCTION manufacturing_order_lot_holding(order_id bigint, lot_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE((
        SELECT SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END)
        FROM manufacturing_productionmaterialmovement m
        JOIN inventory_stocktransfer t ON t.id = m.transfer_id
        JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
        WHERE m.order_id = $1 AND d.lot_id = $2), 0)
    + manufacturing_order_posting_total($1, ARRAY['CONSUME', 'SCRAP'], $2);
$$;

CREATE FUNCTION manufacturing_guard_posting_reversal()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    order_status text;
BEGIN
    SELECT o.status INTO order_status
    FROM manufacturing_orderposting op
    JOIN manufacturing_productionorder o ON o.id = op.order_id
    WHERE op.posting_id = NEW.posting_id
    FOR UPDATE OF o;
    IF order_status IS DISTINCT FROM 'OPEN' THEN
        RAISE EXCEPTION 'a production posting is reversed only while its order is OPEN'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER manufacturing_posting_reversal_open_order
BEFORE INSERT ON inventory_productionpostingreversal FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_posting_reversal();
"""
    + NEW_GUARD
)

REVERSE = (
    r"""
DROP TRIGGER manufacturing_posting_reversal_open_order ON inventory_productionpostingreversal;
DROP FUNCTION manufacturing_guard_posting_reversal();
"""
    + OLD_GUARD
    + OLD_HOLDING
    + r"""
DROP FUNCTION manufacturing_order_net_output(bigint);
DROP FUNCTION manufacturing_order_posting_total(bigint, text[], bigint);
"""
)


class Migration(migrations.Migration):
    dependencies = [
        ("manufacturing", "0006_order_posting_rules"),
        ("inventory", "0014_production_posting_reversal_rules"),
    ]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
