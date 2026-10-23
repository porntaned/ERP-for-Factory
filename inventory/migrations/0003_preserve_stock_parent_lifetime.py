from django.db import migrations


def ledger_foreign_keys(actions):
    # Separate migration: CreateModel's deferred FK SQL has executed after 0002.
    # Retain generated constraint names and resolve the configured actor table.
    return f"""
        DO $$
        DECLARE fk record;
        BEGIN
            IF (SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid = 'inventory_stockledgerentry'::regclass AND contype = 'f') <> 3 THEN
                RAISE EXCEPTION 'expected three stock ledger foreign keys';
            END IF;
            FOR fk IN
                SELECT c.conname, c.confrelid::regclass AS target,
                       local.attname AS local_column, remote.attname AS target_column
                FROM pg_constraint c
                JOIN pg_attribute local ON local.attrelid = c.conrelid
                    AND local.attnum = c.conkey[1]
                JOIN pg_attribute remote ON remote.attrelid = c.confrelid
                    AND remote.attnum = c.confkey[1]
                WHERE c.conrelid = 'inventory_stockledgerentry'::regclass AND c.contype = 'f'
            LOOP
                EXECUTE format('ALTER TABLE inventory_stockledgerentry DROP CONSTRAINT %I',
                               fk.conname);
                EXECUTE format('ALTER TABLE inventory_stockledgerentry ADD CONSTRAINT %I '
                               'FOREIGN KEY (%I) REFERENCES %s (%I) {actions}',
                               fk.conname, fk.local_column, fk.target, fk.target_column);
            END LOOP;
        END;
        $$;
    """


class Migration(migrations.Migration):
    dependencies = [("inventory", "0002_stock_ledger")]

    operations = [
        migrations.RunSQL(
            ledger_foreign_keys("ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE"),
            reverse_sql=ledger_foreign_keys("DEFERRABLE INITIALLY DEFERRED"),
        ),
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION inventory_guard_stock_ancestor_lifetime()
                RETURNS trigger LANGUAGE plpgsql VOLATILE AS $$
                DECLARE has_history boolean;
                BEGIN
                    IF TG_OP = 'UPDATE' THEN
                        IF NEW.id IS NOT DISTINCT FROM OLD.id THEN RETURN NEW; END IF;
                    END IF;
                    -- The append already SHARE-locks Item and Plant. A fixed snapshot
                    -- could otherwise miss history committed before this row lock.
                    IF current_setting('transaction_isolation') <> 'read committed' THEN
                        RAISE EXCEPTION 'stock ancestor replacement requires READ COMMITTED'
                            USING ERRCODE = '23514';
                    END IF;
                    IF TG_TABLE_NAME = 'catalog_item' THEN
                        SELECT EXISTS (
                            SELECT 1 FROM inventory_stockledgerentry entry
                            JOIN inventory_lot lot ON lot.id = entry.lot_id
                            WHERE lot.item_id = OLD.id
                        ) INTO has_history;
                    ELSE
                        SELECT EXISTS (
                            SELECT 1 FROM inventory_stockledgerentry entry
                            JOIN facilities_warehouse warehouse ON warehouse.id = entry.warehouse_id
                            WHERE warehouse.plant_id = OLD.id
                        ) INTO has_history;
                    END IF;
                    IF has_history THEN
                        RAISE EXCEPTION 'stock history ancestor cannot be removed or rekeyed'
                            USING ERRCODE = '23514';
                    END IF;
                    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER inventory_stock_item_lifetime
                BEFORE DELETE OR UPDATE OF id ON catalog_item FOR EACH ROW
                EXECUTE FUNCTION inventory_guard_stock_ancestor_lifetime();
                CREATE TRIGGER inventory_stock_plant_lifetime
                BEFORE DELETE OR UPDATE OF id ON facilities_plant FOR EACH ROW
                EXECUTE FUNCTION inventory_guard_stock_ancestor_lifetime();
            """,
            reverse_sql="""
                DROP TRIGGER inventory_stock_plant_lifetime ON facilities_plant;
                DROP TRIGGER inventory_stock_item_lifetime ON catalog_item;
                DROP FUNCTION inventory_guard_stock_ancestor_lifetime();
            """,
        ),
    ]
