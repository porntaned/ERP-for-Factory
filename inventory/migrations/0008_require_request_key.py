from django.db import migrations

# Legacy StockTransfer rows with NULL request_id stay as history (they predate 0006 and
# are not adopted). A NEW row with no key would bypass the shared registry, so reject it.

REGISTER = """
CREATE OR REPLACE FUNCTION inventory_register_request_key()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    owner_command text;
BEGIN
    IF NEW.request_id IS NULL THEN
        {null_branch}
    END IF;
    INSERT INTO inventory_requestkey (request_id, command)
    VALUES (NEW.request_id, TG_ARGV[0])
    ON CONFLICT (request_id) DO NOTHING;
    SELECT command INTO owner_command
    FROM inventory_requestkey WHERE request_id = NEW.request_id;
    IF owner_command IS DISTINCT FROM TG_ARGV[0] THEN
        RAISE EXCEPTION 'request_id already used by another command'
            USING ERRCODE = '23505';
    END IF;
    RETURN NEW;
END;
$$;
"""

REJECT_NULL = (
    "RAISE EXCEPTION 'request_id is required for new % rows', TG_ARGV[0] USING ERRCODE = '23502';"
)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_request_key_registry"),
        ("quality", "0004_request_key_registration"),
    ]

    operations = [
        migrations.RunSQL(
            sql=REGISTER.format(null_branch=REJECT_NULL),
            reverse_sql=REGISTER.format(null_branch="RETURN NEW;"),
        ),
    ]
