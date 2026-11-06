"""M6.2 (Issue #103): PostgreSQL refuses stock entries for a REJECTED Lot, checked at commit.

While the Lot of a NEW ledger entry is REJECTED at any warehouse (its latest disposition event
there is REJECTED), the entry must be a debit linked as one of:
- a ProductionPosting of kind SCRAP;
- the debit entry of a StockReversal of a receipt;
- the entry of a ProductionPostingReversal whose posting is an OUTPUT.
Anything else, including an entry with no link, fails the commit.

The trigger is a deferred constraint trigger on the ledger entry: the entry is inserted before the
row that links it, in the same transaction, and every stock change creates one, so a direct INSERT
is covered too. Checked on insert only: history written before this migration is never re-checked.
Quality and Inventory both take the Lot row lock first and hold it to commit, so a rejection and a
movement of the same Lot serialize (a raw INSERT takes a key-share lock on the Lot through its
foreign key, which a rejection's FOR UPDATE waits for).
"""

from django.db import migrations

FORWARD = r"""
CREATE FUNCTION inventory_guard_rejected_lot()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM (
            SELECT DISTINCT ON (e.warehouse_id) e.to_disposition
            FROM quality_lotdispositionevent e
            WHERE e.lot_id = NEW.lot_id
            ORDER BY e.warehouse_id, e.id DESC) latest
        WHERE latest.to_disposition = 'REJECTED') THEN
        RETURN NULL;
    END IF;
    IF NEW.quantity_delta < 0 AND (
        EXISTS (SELECT 1 FROM inventory_productionposting p
                WHERE p.ledger_entry_id = NEW.id AND p.kind = 'SCRAP')
        OR EXISTS (SELECT 1 FROM inventory_stockreversal r
                   WHERE r.debit_entry_id = NEW.id AND r.receipt_id IS NOT NULL)
        OR EXISTS (SELECT 1 FROM inventory_productionpostingreversal v
                   JOIN inventory_productionposting p ON p.id = v.posting_id
                   WHERE v.ledger_entry_id = NEW.id AND p.kind = 'OUTPUT')) THEN
        RETURN NULL;
    END IF;
    RAISE EXCEPTION 'Lot is REJECTED: only a SCRAP, a receipt reversal or an OUTPUT reversal '
        'may take its stock out' USING ERRCODE = '23514';
END;
$$;
CREATE CONSTRAINT TRIGGER inventory_ledger_rejected_lot_guard
AFTER INSERT ON inventory_stockledgerentry DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION inventory_guard_rejected_lot();
"""

REVERSE = r"""
DROP TRIGGER inventory_ledger_rejected_lot_guard ON inventory_stockledgerentry;
DROP FUNCTION inventory_guard_rejected_lot();
"""


def fire_pending():
    return migrations.RunSQL(
        sql="SET CONSTRAINTS ALL IMMEDIATE;", reverse_sql="SET CONSTRAINTS ALL IMMEDIATE;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0014_production_posting_reversal_rules"),
        ("quality", "0007_inspection_transition_rules"),
    ]

    operations = [
        # Fire deferred checks from earlier work in this transaction before adding the trigger.
        fire_pending(),
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
        # Runs first when unapplying: fire pending deferred checks before the trigger is dropped.
        fire_pending(),
    ]
