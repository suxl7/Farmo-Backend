# Manual migration to fix index issues

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0022_remove_product_valid_payment_method_accepted_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT indexname FROM pg_indexes WHERE indexname LIKE '%_like' AND schemaname = 'public') LOOP
                        EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.indexname);
                    END LOOP;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
