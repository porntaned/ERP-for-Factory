"""M5.2c (Issue #81): PostgreSQL rules for production posting reversals.

A reversal entry exactly offsets its posting (same Lot and warehouse, opposite quantity) and
belongs to nothing else, in either direction of adoption. An OUTPUT is reversible only while
every other entry of its Lot is an OUTPUT posting or the reversal of one. Reversals are
immutable and their keys join the shared registry (POSTING_REV), registered last.
"""

from django.db import migrations

FORWARD = r"""
ALTER TABLE inventory_productionpostingreversal ALTER COLUMN id SET GENERATED ALWAYS;

CREATE FUNCTION inventory_production_lot_only_outputs(lot bigint, except_entry bigint)
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT NOT EXISTS (
        SELECT 1 FROM inventory_stockledgerentry l
        WHERE l.lot_id = $1 AND l.id <> $2
          AND NOT EXISTS (SELECT 1 FROM inventory_productionposting p
                          WHERE p.ledger_entry_id = l.id AND p.kind = 'OUTPUT')
          AND NOT EXISTS (SELECT 1 FROM inventory_productionpostingreversal r
                          JOIN inventory_productionposting p ON p.id = r.posting_id
                          WHERE r.ledger_entry_id = l.id AND p.kind = 'OUTPUT')
    );
$$;

CREATE FUNCTION inventory_validate_production_reversal()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    original record;
    entry record;
BEGIN
    SELECT * INTO entry FROM inventory_stockledgerentry WHERE id = NEW.ledger_entry_id FOR UPDATE;
    SELECT p.kind, l.lot_id, l.warehouse_id, l.quantity_delta INTO original
    FROM inventory_productionposting p
    JOIN inventory_stockledgerentry l ON l.id = p.ledger_entry_id
    WHERE p.id = NEW.posting_id;
    IF original.kind IS NULL OR entry.id IS NULL
       OR entry.lot_id <> original.lot_id
       OR entry.warehouse_id <> original.warehouse_id
       OR entry.quantity_delta <> -original.quantity_delta THEN
        RAISE EXCEPTION 'a production reversal must exactly offset its posting'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (SELECT 1 FROM inventory_stockreceipt WHERE ledger_entry_id = NEW.ledger_entry_id)
       OR EXISTS (SELECT 1 FROM inventory_stocktransfer
                  WHERE NEW.ledger_entry_id IN (source_entry_id, destination_entry_id))
       OR EXISTS (SELECT 1 FROM inventory_stockreversal
                  WHERE NEW.ledger_entry_id IN (debit_entry_id, credit_entry_id))
       OR EXISTS (SELECT 1 FROM inventory_productionposting
                  WHERE ledger_entry_id = NEW.ledger_entry_id) THEN
        RAISE EXCEPTION 'a production reversal entry belongs to nothing else'
            USING ERRCODE = '23514';
    END IF;
    IF original.kind = 'OUTPUT'
       AND NOT inventory_production_lot_only_outputs(original.lot_id, NEW.ledger_entry_id) THEN
        RAISE EXCEPTION 'an output Lot that was used or moved cannot be reversed'
            USING ERRCODE = '23514';
    END IF;
    NEW.created_at := statement_timestamp();
    RETURN NEW;
END;
$$;
CREATE TRIGGER inventory_production_reversal_link
BEFORE INSERT ON inventory_productionpostingreversal FOR EACH ROW
EXECUTE FUNCTION inventory_validate_production_reversal();
CREATE TRIGGER inventory_production_reversal_immutable
BEFORE UPDATE OR DELETE ON inventory_productionpostingreversal FOR EACH ROW
EXECUTE FUNCTION inventory_reject_stock_rewrite();
CREATE TRIGGER inventory_production_reversal_zz_request_key
BEFORE INSERT ON inventory_productionpostingreversal FOR EACH ROW
EXECUTE FUNCTION inventory_register_request_key('POSTING_REV');

CREATE FUNCTION inventory_reject_production_reversal_adoption()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    entry_ids bigint[];
BEGIN
    IF TG_TABLE_NAME IN ('inventory_stockreceipt', 'inventory_productionposting') THEN
        entry_ids := ARRAY[NEW.ledger_entry_id];
    ELSIF TG_TABLE_NAME = 'inventory_stocktransfer' THEN
        entry_ids := ARRAY[NEW.source_entry_id, NEW.destination_entry_id];
    ELSE
        entry_ids := ARRAY[NEW.debit_entry_id, NEW.credit_entry_id];
    END IF;
    IF EXISTS (SELECT 1 FROM inventory_productionpostingreversal
               WHERE ledger_entry_id = ANY(entry_ids)) THEN
        RAISE EXCEPTION 'a production reversal entry belongs to nothing else'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER inventory_receipt_not_production_reversal
BEFORE INSERT ON inventory_stockreceipt FOR EACH ROW
EXECUTE FUNCTION inventory_reject_production_reversal_adoption();
CREATE TRIGGER inventory_transfer_not_production_reversal
BEFORE INSERT ON inventory_stocktransfer FOR EACH ROW
EXECUTE FUNCTION inventory_reject_production_reversal_adoption();
CREATE TRIGGER inventory_reversal_not_production_reversal
BEFORE INSERT ON inventory_stockreversal FOR EACH ROW
EXECUTE FUNCTION inventory_reject_production_reversal_adoption();
CREATE TRIGGER inventory_posting_not_production_reversal
BEFORE INSERT ON inventory_productionposting FOR EACH ROW
EXECUTE FUNCTION inventory_reject_production_reversal_adoption();
"""

REVERSE = r"""
LOCK TABLE inventory_productionpostingreversal IN ACCESS EXCLUSIVE MODE;
-- Unapplying would leave reversal entries in the immutable ledger unexplained. Refuse.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM inventory_productionpostingreversal) THEN
        RAISE EXCEPTION 'cannot unapply 0014 while production reversals exist'
            USING ERRCODE = '23514';
    END IF;
END;
$$;
DROP TRIGGER inventory_posting_not_production_reversal ON inventory_productionposting;
DROP TRIGGER inventory_reversal_not_production_reversal ON inventory_stockreversal;
DROP TRIGGER inventory_transfer_not_production_reversal ON inventory_stocktransfer;
DROP TRIGGER inventory_receipt_not_production_reversal ON inventory_stockreceipt;
DROP FUNCTION inventory_reject_production_reversal_adoption();
DROP TRIGGER inventory_production_reversal_zz_request_key ON inventory_productionpostingreversal;
DROP TRIGGER inventory_production_reversal_immutable ON inventory_productionpostingreversal;
DROP TRIGGER inventory_production_reversal_link ON inventory_productionpostingreversal;
DROP FUNCTION inventory_validate_production_reversal();
DROP FUNCTION inventory_production_lot_only_outputs(bigint, bigint);
ALTER TABLE inventory_productionpostingreversal ALTER COLUMN id SET GENERATED BY DEFAULT;
"""


class Migration(migrations.Migration):
    dependencies = [("inventory", "0013_production_posting_reversal")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
