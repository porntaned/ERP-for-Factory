from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("quality", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION quality_validate_lot_disposition_insert_v2()
                RETURNS trigger LANGUAGE plpgsql AS $$
                DECLARE
                    item_id bigint;
                    plant_id bigint;
                    lot_organization_id bigint;
                    warehouse_organization_id bigint;
                    latest_id bigint;
                    current_disposition varchar(8);
                BEGIN
                    NEW.created_at := statement_timestamp();

                    -- Match the identity guards' row locks before reading their edges.
                    -- SHARE prevents even non-key FK reassignment, unlike KEY SHARE.
                    SELECT lot.item_id INTO item_id
                    FROM inventory_lot AS lot WHERE lot.id = NEW.lot_id FOR UPDATE;
                    SELECT item.organization_id INTO lot_organization_id
                    FROM catalog_item AS item WHERE item.id = item_id FOR SHARE;
                    SELECT warehouse.plant_id INTO plant_id
                    FROM facilities_warehouse AS warehouse
                    WHERE warehouse.id = NEW.warehouse_id FOR SHARE;
                    SELECT plant.organization_id INTO warehouse_organization_id
                    FROM facilities_plant AS plant WHERE plant.id = plant_id FOR SHARE;

                    IF lot_organization_id IS NOT NULL
                       AND warehouse_organization_id IS NOT NULL
                       AND lot_organization_id <> warehouse_organization_id THEN
                        RAISE EXCEPTION 'lot and warehouse belong to different organizations'
                            USING ERRCODE = '23514';
                    END IF;

                    SELECT event.id, event.to_disposition
                    INTO latest_id, current_disposition
                    FROM quality_lotdispositionevent AS event
                    WHERE event.lot_id = NEW.lot_id
                      AND event.warehouse_id = NEW.warehouse_id
                    ORDER BY event.id DESC LIMIT 1;

                    IF latest_id IS NOT NULL AND NEW.id <= latest_id THEN
                        RAISE EXCEPTION 'disposition event id must increase within its history'
                            USING ERRCODE = '23514';
                    END IF;
                    current_disposition := COALESCE(current_disposition, 'HOLD');
                    IF NEW.from_disposition IS NOT NULL
                       AND NEW.from_disposition <> current_disposition THEN
                        RAISE EXCEPTION 'invalid disposition chain: expected %, received %',
                            current_disposition, NEW.from_disposition
                            USING ERRCODE = '23514';
                    END IF;
                    RETURN NEW;
                END;
                $$;

                DROP TRIGGER quality_lot_disposition_validate_insert
                    ON quality_lotdispositionevent;
                CREATE TRIGGER quality_lot_disposition_validate_insert
                BEFORE INSERT ON quality_lotdispositionevent FOR EACH ROW
                EXECUTE FUNCTION quality_validate_lot_disposition_insert_v2();

                CREATE FUNCTION quality_guard_history_identity()
                RETURNS trigger LANGUAGE plpgsql AS $$
                DECLARE
                    has_history boolean;
                BEGIN
                    IF TG_TABLE_NAME = 'inventory_lot' THEN
                        IF NEW.item_id IS NOT DISTINCT FROM OLD.item_id THEN
                            RETURN NEW;
                        END IF;
                        SELECT EXISTS (
                            SELECT 1 FROM quality_lotdispositionevent WHERE lot_id = OLD.id
                        ) INTO has_history;
                    ELSIF TG_TABLE_NAME = 'catalog_item' THEN
                        IF NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id THEN
                            RETURN NEW;
                        END IF;
                        SELECT EXISTS (
                            SELECT 1 FROM quality_lotdispositionevent AS event
                            JOIN inventory_lot AS lot ON lot.id = event.lot_id
                            WHERE lot.item_id = OLD.id
                        ) INTO has_history;
                    ELSIF TG_TABLE_NAME = 'facilities_warehouse' THEN
                        IF NEW.plant_id IS NOT DISTINCT FROM OLD.plant_id THEN
                            RETURN NEW;
                        END IF;
                        SELECT EXISTS (
                            SELECT 1 FROM quality_lotdispositionevent
                            WHERE warehouse_id = OLD.id
                        ) INTO has_history;
                    ELSE
                        IF NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id THEN
                            RETURN NEW;
                        END IF;
                        SELECT EXISTS (
                            SELECT 1 FROM quality_lotdispositionevent AS event
                            JOIN facilities_warehouse AS warehouse
                                ON warehouse.id = event.warehouse_id
                            WHERE warehouse.plant_id = OLD.id
                        ) INTO has_history;
                    END IF;
                    IF has_history THEN
                        RAISE EXCEPTION 'recorded disposition identity cannot be reassigned'
                            USING ERRCODE = '23514';
                    END IF;
                    RETURN NEW;
                END;
                $$;

                CREATE TRIGGER quality_guard_lot_identity
                BEFORE UPDATE OF item_id ON inventory_lot FOR EACH ROW
                EXECUTE FUNCTION quality_guard_history_identity();
                CREATE TRIGGER quality_guard_item_identity
                BEFORE UPDATE OF organization_id ON catalog_item FOR EACH ROW
                EXECUTE FUNCTION quality_guard_history_identity();
                CREATE TRIGGER quality_guard_warehouse_identity
                BEFORE UPDATE OF plant_id ON facilities_warehouse FOR EACH ROW
                EXECUTE FUNCTION quality_guard_history_identity();
                CREATE TRIGGER quality_guard_plant_identity
                BEFORE UPDATE OF organization_id ON facilities_plant FOR EACH ROW
                EXECUTE FUNCTION quality_guard_history_identity();
            """,
            reverse_sql="""
                DROP TRIGGER quality_guard_lot_identity ON inventory_lot;
                DROP TRIGGER quality_guard_item_identity ON catalog_item;
                DROP TRIGGER quality_guard_warehouse_identity ON facilities_warehouse;
                DROP TRIGGER quality_guard_plant_identity ON facilities_plant;
                DROP FUNCTION quality_guard_history_identity();
                DROP TRIGGER quality_lot_disposition_validate_insert
                    ON quality_lotdispositionevent;
                CREATE TRIGGER quality_lot_disposition_validate_insert
                BEFORE INSERT ON quality_lotdispositionevent FOR EACH ROW
                EXECUTE FUNCTION quality_validate_lot_disposition_insert();
                DROP FUNCTION quality_validate_lot_disposition_insert_v2();
            """,
        ),
    ]
