from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("quality", "0003_authoritative_event_identity"),
        ("inventory", "0007_request_key_registry"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Abort with no partial state if a disposition UUID was already used by a
                -- receipt or transfer; never choose a winner.
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM quality_lotdispositionevent event
                        JOIN inventory_requestkey key ON key.request_id = event.request_id
                        WHERE key.command <> 'DISPOSITION'
                    ) THEN
                        RAISE EXCEPTION 'disposition request_id already used by another command'
                            USING ERRCODE = '23505';
                    END IF;
                END;
                $$;

                INSERT INTO inventory_requestkey (request_id, command)
                SELECT request_id, 'DISPOSITION' FROM quality_lotdispositionevent
                ON CONFLICT (request_id) DO NOTHING;

                CREATE TRIGGER quality_disposition_request_key
                BEFORE INSERT ON quality_lotdispositionevent FOR EACH ROW
                EXECUTE FUNCTION inventory_register_request_key('DISPOSITION');
            """,
            reverse_sql="""
                DROP TRIGGER quality_disposition_request_key ON quality_lotdispositionevent;
                ALTER TABLE inventory_requestkey DISABLE TRIGGER inventory_requestkey_immutable;
                DELETE FROM inventory_requestkey WHERE command = 'DISPOSITION';
                ALTER TABLE inventory_requestkey ENABLE TRIGGER inventory_requestkey_immutable;
            """,
        ),
    ]
