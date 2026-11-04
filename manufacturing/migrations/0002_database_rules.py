"""M5.1 (Issue #69): rules PostgreSQL enforces for every writer, including raw SQL.

- BOM: inserted as DRAFT for a FINISHED/WIP item; identity never changes; status moves only
  DRAFT -> ACTIVE -> RETIRED and approval is written once; never deleted.
- BOM line: only while its BOM is DRAFT; component RAW/WIP, same organization, not the item.
- Order: inserted only on an ACTIVE BOM (read FOR SHARE, so it queues behind an approval);
  both warehouses in one plant of the item's organization; only OPEN -> CANCELLED; no deletes.
- Request keys join inventory's shared registry. Key triggers are named *_zz_* so they run
  after the guards (PostgreSQL fires same-event triggers alphabetically).
"""

from django.db import migrations

FORWARD = r"""
ALTER TABLE manufacturing_billofmaterials ALTER COLUMN id SET GENERATED ALWAYS;
ALTER TABLE manufacturing_bomline ALTER COLUMN id SET GENERATED ALWAYS;
ALTER TABLE manufacturing_productionorder ALTER COLUMN id SET GENERATED ALWAYS;

-- Same insert-or-keep logic as inventory_register_request_key(), but the key column is an
-- argument so UPDATE-time keys (approval, cancel) register when they go from NULL to a value.
CREATE FUNCTION manufacturing_register_request_key()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    new_key uuid := (to_jsonb(NEW) ->> TG_ARGV[1])::uuid;
    owner_command text;
BEGIN
    IF new_key IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND new_key IS NOT DISTINCT FROM (to_jsonb(OLD) ->> TG_ARGV[1])::uuid THEN
        RETURN NEW;
    END IF;
    INSERT INTO inventory_requestkey (request_id, command)
    VALUES (new_key, TG_ARGV[0])
    ON CONFLICT (request_id) DO NOTHING;
    SELECT command INTO owner_command FROM inventory_requestkey WHERE request_id = new_key;
    IF owner_command IS DISTINCT FROM TG_ARGV[0] THEN
        RAISE EXCEPTION 'request_id already used by another command' USING ERRCODE = '23505';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION manufacturing_guard_bom()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    kind text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'bills of materials are never deleted' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'DRAFT' THEN
            RAISE EXCEPTION 'a BOM is created as DRAFT' USING ERRCODE = '23514';
        END IF;
        SELECT item_type INTO kind FROM catalog_item WHERE id = NEW.item_id;
        IF kind IS DISTINCT FROM 'FINISHED' AND kind IS DISTINCT FROM 'WIP' THEN
            RAISE EXCEPTION 'a BOM is for a FINISHED or WIP item' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.item_id <> OLD.item_id OR NEW.version <> OLD.version
        OR NEW.created_by_id <> OLD.created_by_id OR NEW.created_at <> OLD.created_at
        OR NEW.request_id <> OLD.request_id THEN
        RAISE EXCEPTION 'BOM identity is immutable' USING ERRCODE = '23514';
    END IF;
    IF OLD.status = 'DRAFT' AND NEW.status = 'ACTIVE' THEN
        RETURN NEW;  -- approval fields are written here; the CHECK requires all of them
    END IF;
    IF NEW.approved_by_id IS DISTINCT FROM OLD.approved_by_id
        OR NEW.approved_at IS DISTINCT FROM OLD.approved_at
        OR NEW.approval_request_id IS DISTINCT FROM OLD.approval_request_id THEN
        RAISE EXCEPTION 'BOM approval is written once' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = OLD.status OR (OLD.status = 'ACTIVE' AND NEW.status = 'RETIRED') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'BOM status moves only DRAFT -> ACTIVE -> RETIRED' USING ERRCODE = '23514';
END;
$$;

CREATE TRIGGER manufacturing_bom_guard
BEFORE INSERT OR UPDATE OR DELETE ON manufacturing_billofmaterials FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_bom();
CREATE TRIGGER manufacturing_bom_zz_request_key
BEFORE INSERT ON manufacturing_billofmaterials FOR EACH ROW
EXECUTE FUNCTION manufacturing_register_request_key('BOM_DRAFT', 'request_id');
CREATE TRIGGER manufacturing_bom_zz_approval_key
BEFORE UPDATE ON manufacturing_billofmaterials FOR EACH ROW
EXECUTE FUNCTION manufacturing_register_request_key('BOM_APPROVE', 'approval_request_id');

-- FOR SHARE on the header queues a line change behind a concurrent approval's row lock.
CREATE FUNCTION manufacturing_guard_bom_line()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    header_status text;
    header_item bigint;
    header_org bigint;
    component_kind text;
    component_org bigint;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        SELECT status INTO header_status
        FROM manufacturing_billofmaterials WHERE id = OLD.bom_id FOR SHARE;
        IF header_status IS DISTINCT FROM 'DRAFT' THEN
            RAISE EXCEPTION 'BOM lines are locked once the BOM leaves DRAFT'
                USING ERRCODE = '23514';
        END IF;
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        IF NEW.bom_id <> OLD.bom_id THEN
            RAISE EXCEPTION 'a BOM line never moves to another BOM' USING ERRCODE = '23514';
        END IF;
    END IF;
    SELECT b.status, b.item_id, i.organization_id INTO header_status, header_item, header_org
    FROM manufacturing_billofmaterials b JOIN catalog_item i ON i.id = b.item_id
    WHERE b.id = NEW.bom_id FOR SHARE OF b;
    IF header_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'BOM lines are locked once the BOM leaves DRAFT' USING ERRCODE = '23514';
    END IF;
    SELECT item_type, organization_id INTO component_kind, component_org
    FROM catalog_item WHERE id = NEW.component_id;
    IF component_kind IS DISTINCT FROM 'RAW' AND component_kind IS DISTINCT FROM 'WIP' THEN
        RAISE EXCEPTION 'a BOM component is a RAW or WIP item' USING ERRCODE = '23514';
    END IF;
    IF component_org IS DISTINCT FROM header_org THEN
        RAISE EXCEPTION 'a BOM component belongs to the BOM item organization'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.component_id = header_item THEN
        RAISE EXCEPTION 'a BOM item cannot be its own component' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_bom_line_guard
BEFORE INSERT OR UPDATE OR DELETE ON manufacturing_bomline FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_bom_line();

CREATE FUNCTION manufacturing_guard_order()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    bom_status text;
    item_org bigint;
    line_plant bigint;
    output_plant bigint;
    plant_org bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'production orders are never deleted' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF NEW.bom_id <> OLD.bom_id OR NEW.quantity <> OLD.quantity
            OR NEW.line_warehouse_id <> OLD.line_warehouse_id
            OR NEW.output_warehouse_id <> OLD.output_warehouse_id
            OR NEW.created_by_id <> OLD.created_by_id OR NEW.created_at <> OLD.created_at
            OR NEW.request_id <> OLD.request_id THEN
            RAISE EXCEPTION 'production order identity is immutable' USING ERRCODE = '23514';
        END IF;
        IF OLD.status = 'OPEN' AND NEW.status = 'CANCELLED' THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'a production order moves only OPEN -> CANCELLED'
            USING ERRCODE = '23514';
    END IF;
    SELECT b.status, i.organization_id INTO bom_status, item_org
    FROM manufacturing_billofmaterials b JOIN catalog_item i ON i.id = b.item_id
    WHERE b.id = NEW.bom_id FOR SHARE OF b;
    IF bom_status IS DISTINCT FROM 'ACTIVE' THEN
        RAISE EXCEPTION 'a production order needs an ACTIVE BOM' USING ERRCODE = '23514';
    END IF;
    SELECT plant_id INTO line_plant FROM facilities_warehouse WHERE id = NEW.line_warehouse_id;
    SELECT plant_id INTO output_plant FROM facilities_warehouse WHERE id = NEW.output_warehouse_id;
    SELECT organization_id INTO plant_org FROM facilities_plant WHERE id = line_plant;
    IF line_plant IS DISTINCT FROM output_plant OR plant_org IS DISTINCT FROM item_org THEN
        RAISE EXCEPTION 'order warehouses share one plant of the item organization'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER manufacturing_order_guard
BEFORE INSERT OR UPDATE OR DELETE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_order();
CREATE TRIGGER manufacturing_order_zz_request_key
BEFORE INSERT ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_register_request_key('ORDER_CREATE', 'request_id');
CREATE TRIGGER manufacturing_order_zz_cancel_key
BEFORE UPDATE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_register_request_key('ORDER_CANCEL', 'cancel_request_id');
"""

REVERSE = r"""
DROP TRIGGER manufacturing_order_zz_cancel_key ON manufacturing_productionorder;
DROP TRIGGER manufacturing_order_zz_request_key ON manufacturing_productionorder;
DROP TRIGGER manufacturing_order_guard ON manufacturing_productionorder;
DROP FUNCTION manufacturing_guard_order();
DROP TRIGGER manufacturing_bom_line_guard ON manufacturing_bomline;
DROP FUNCTION manufacturing_guard_bom_line();
DROP TRIGGER manufacturing_bom_zz_approval_key ON manufacturing_billofmaterials;
DROP TRIGGER manufacturing_bom_zz_request_key ON manufacturing_billofmaterials;
DROP TRIGGER manufacturing_bom_guard ON manufacturing_billofmaterials;
DROP FUNCTION manufacturing_guard_bom();
DROP FUNCTION manufacturing_register_request_key();
ALTER TABLE manufacturing_productionorder ALTER COLUMN id SET GENERATED BY DEFAULT;
ALTER TABLE manufacturing_bomline ALTER COLUMN id SET GENERATED BY DEFAULT;
ALTER TABLE manufacturing_billofmaterials ALTER COLUMN id SET GENERATED BY DEFAULT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("manufacturing", "0001_initial"),
        ("inventory", "0010_manufacturing_request_keys"),
    ]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
