"""M6.1 (Issue #96): only an inspection moves a Lot-Warehouse out of HOLD.

- HOLD -> RELEASED / REJECTED must carry an inspection of the same Lot and warehouse whose
  result matches (PASS -> RELEASED, FAIL -> REJECTED).
- Any other event carries no inspection and is RELEASED -> HOLD or REJECTED -> HOLD.
- REJECTED -> HOLD needs an APPROVER grant at the warehouse for an actor who is not the
  inspector of the latest rejection there.

Checked on insert only, so history written before M6.1 stays valid. The trigger name sorts after
quality_lot_disposition_validate_insert (which takes the Lot lock) and before the request key.
"""

from django.db import migrations

FORWARD = r"""
CREATE FUNCTION quality_guard_disposition_inspection()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    found quality_lotinspection%ROWTYPE;
    rejecting_inspector bigint;
BEGIN
    IF NEW.from_disposition = 'HOLD' AND NEW.to_disposition IN ('RELEASED', 'REJECTED') THEN
        SELECT * INTO found FROM quality_lotinspection WHERE id = NEW.inspection_id;
        IF found.id IS NULL
           OR found.lot_id <> NEW.lot_id
           OR found.warehouse_id <> NEW.warehouse_id
           OR (found.result = 'PASS') <> (NEW.to_disposition = 'RELEASED') THEN
            RAISE EXCEPTION 'leaving HOLD needs a matching inspection of this Lot and warehouse'
                USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.inspection_id IS NOT NULL THEN
        RAISE EXCEPTION 'only an event leaving HOLD carries an inspection'
            USING ERRCODE = '23514';
    END IF;
    IF NOT ((NEW.from_disposition, NEW.to_disposition) IN (('RELEASED', 'HOLD'),
                                                           ('REJECTED', 'HOLD'))) THEN
        RAISE EXCEPTION 'disposition change % -> % is not allowed', NEW.from_disposition,
            NEW.to_disposition USING ERRCODE = '23514';
    END IF;
    IF NEW.from_disposition = 'REJECTED' THEN
        IF NOT EXISTS (
            SELECT 1 FROM access_control_warehouseroleassignment g
            WHERE g.user_id = NEW.actor_id AND g.warehouse_id = NEW.warehouse_id
              AND g.role = 'APPROVER') THEN
            RAISE EXCEPTION 'returning a REJECTED Lot to HOLD needs an APPROVER grant'
                USING ERRCODE = '23514';
        END IF;
        SELECT i.inspector_id INTO rejecting_inspector
        FROM quality_lotdispositionevent e
        JOIN quality_lotinspection i ON i.id = e.inspection_id
        WHERE e.lot_id = NEW.lot_id AND e.warehouse_id = NEW.warehouse_id
          AND e.to_disposition = 'REJECTED'
        ORDER BY e.id DESC LIMIT 1;
        IF rejecting_inspector = NEW.actor_id THEN
            RAISE EXCEPTION 'the inspector who rejected this Lot cannot return it to HOLD'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER quality_lot_disposition_w_inspection_rules
BEFORE INSERT ON quality_lotdispositionevent FOR EACH ROW
EXECUTE FUNCTION quality_guard_disposition_inspection();
"""

REVERSE = r"""
DROP TRIGGER quality_lot_disposition_w_inspection_rules ON quality_lotdispositionevent;
DROP FUNCTION quality_guard_disposition_inspection();
"""


class Migration(migrations.Migration):
    dependencies = [("quality", "0006_lot_inspection")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
