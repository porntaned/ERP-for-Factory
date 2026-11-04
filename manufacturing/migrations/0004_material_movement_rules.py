"""M5.2a (Issue #72): rules for issue/return movements, enforced for every writer.

On insert the order row is locked FOR UPDATE, so concurrent movements of one order queue and
each sees the committed net issue. A movement is never updated or deleted. An order cannot be
cancelled while it still holds material on its line.
"""

from django.db import migrations

FORWARD = r"""
ALTER TABLE manufacturing_productionmaterialmovement ALTER COLUMN id SET GENERATED ALWAYS;

-- Net quantity of one Lot the order holds on its line (issued - returned).
CREATE FUNCTION manufacturing_order_lot_holding(order_id bigint, lot_id bigint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE(SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END), 0)
    FROM manufacturing_productionmaterialmovement m
    JOIN inventory_stocktransfer t ON t.id = m.transfer_id
    JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
    WHERE m.order_id = $1 AND d.lot_id = $2;
$$;

CREATE FUNCTION manufacturing_guard_material_movement()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    o record;
    src record;
    dst record;
    component bigint;
    per numeric;
    net numeric;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'material movements are immutable' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO o FROM manufacturing_productionorder WHERE id = NEW.order_id FOR UPDATE;
    IF o.status IS DISTINCT FROM 'OPEN' THEN
        RAISE EXCEPTION 'material moves only for an OPEN order' USING ERRCODE = '23514';
    END IF;
    SELECT s.lot_id, s.warehouse_id INTO src
    FROM inventory_stocktransfer t JOIN inventory_stockledgerentry s ON s.id = t.source_entry_id
    WHERE t.id = NEW.transfer_id;
    SELECT d.warehouse_id, d.quantity_delta AS quantity INTO dst
    FROM inventory_stocktransfer t JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
    WHERE t.id = NEW.transfer_id;
    IF NEW.kind = 'ISSUE' AND NOT (dst.warehouse_id = o.line_warehouse_id
                                   AND src.warehouse_id <> o.line_warehouse_id) THEN
        RAISE EXCEPTION 'an issue moves material onto the order line' USING ERRCODE = '23514';
    END IF;
    IF NEW.kind = 'RETURN' AND NOT (src.warehouse_id = o.line_warehouse_id
                                    AND dst.warehouse_id <> o.line_warehouse_id) THEN
        RAISE EXCEPTION 'a return moves material off the order line' USING ERRCODE = '23514';
    END IF;
    SELECT lot.item_id INTO component FROM inventory_lot lot WHERE lot.id = src.lot_id;
    SELECT l.quantity_per INTO per
    FROM manufacturing_bomline l WHERE l.bom_id = o.bom_id AND l.component_id = component;
    IF per IS NULL THEN
        RAISE EXCEPTION 'the Lot item is not a component of the order BOM' USING ERRCODE = '23514';
    END IF;
    SELECT COALESCE(SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END), 0)
    INTO net
    FROM manufacturing_productionmaterialmovement m
    JOIN inventory_stocktransfer t ON t.id = m.transfer_id
    JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
    JOIN inventory_lot lot ON lot.id = d.lot_id
    WHERE m.order_id = NEW.order_id AND lot.item_id = component;
    net := net + CASE NEW.kind WHEN 'ISSUE' THEN dst.quantity ELSE -dst.quantity END;
    IF net > o.quantity * per THEN
        RAISE EXCEPTION 'net issue exceeds the BOM requirement' USING ERRCODE = '23514';
    END IF;
    IF NEW.kind = 'RETURN'
       AND manufacturing_order_lot_holding(NEW.order_id, src.lot_id) < dst.quantity THEN
        RAISE EXCEPTION 'a return exceeds what the order holds of this Lot' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_material_movement_guard
BEFORE INSERT OR UPDATE OR DELETE ON manufacturing_productionmaterialmovement FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_material_movement();

CREATE FUNCTION manufacturing_guard_order_cancel_holding()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'OPEN' AND NEW.status = 'CANCELLED' AND EXISTS (
        SELECT 1 FROM manufacturing_productionmaterialmovement m
        JOIN inventory_stocktransfer t ON t.id = m.transfer_id
        JOIN inventory_stockledgerentry d ON d.id = t.destination_entry_id
        WHERE m.order_id = NEW.id
        GROUP BY d.lot_id
        HAVING SUM(CASE m.kind WHEN 'ISSUE' THEN d.quantity_delta ELSE -d.quantity_delta END) <> 0
    ) THEN
        RAISE EXCEPTION 'an order holding material on its line cannot be cancelled'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_order_cancel_holding
BEFORE UPDATE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_order_cancel_holding();
"""

REVERSE = r"""
DROP TRIGGER manufacturing_order_cancel_holding ON manufacturing_productionorder;
DROP FUNCTION manufacturing_guard_order_cancel_holding();
DROP TRIGGER manufacturing_material_movement_guard ON manufacturing_productionmaterialmovement;
DROP FUNCTION manufacturing_guard_material_movement();
DROP FUNCTION manufacturing_order_lot_holding(bigint, bigint);
ALTER TABLE manufacturing_productionmaterialmovement ALTER COLUMN id SET GENERATED BY DEFAULT;
"""


class Migration(migrations.Migration):
    dependencies = [("manufacturing", "0003_material_movement")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
