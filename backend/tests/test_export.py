import os
import re
import secrets

import pytest
import sqlparse

from app.export import export_dataset, sql_literal


@pytest.mark.parametrize("dataset", ["online-store", "inventory"])
def test_export_contains_only_public_setup(dataset):
    script = export_dataset(dataset)
    assert "CREATE DATABASE `querylab_" in script
    assert not re.search(r"(?im)^\s*(DROP|GRANT|REVOKE|CREATE USER|SET GLOBAL)\b", script)
    assert script == export_dataset(dataset)
    assert "COMMIT;" in script
    if dataset == "online-store":
        assert "Maya Chen" in script
        assert "Maya Chen 1" not in script
        assert "seed-a0" in script and "seed-a1" not in script


def test_export_rejects_unknown_dataset_and_foreign_schema():
    with pytest.raises(ValueError):
        export_dataset("unknown")
    with pytest.raises(ValueError):
        export_dataset("online-store", "personal_database")
    with pytest.raises(ValueError):
        export_dataset("online-store", "querylab_foo`; DROP DATABASE mysql; --")


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
@pytest.mark.parametrize("dataset", ["online-store", "inventory"])
def test_download_imports_real_mysql_and_preserves_other_data(dataset):
    from app.engine import connect
    schema = "querylab_export_test_" + secrets.token_hex(6)
    sentinel = "querylab_export_keep_" + secrets.token_hex(6)
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{sentinel}`")
            cursor.execute(f"CREATE TABLE `{sentinel}`.keep_me(value INT)")
            cursor.execute(f"INSERT INTO `{sentinel}`.keep_me VALUES(42)")
            # This is an authored setup file for a MySQL client, not a learner
            # Run script subject to the editor's statement-count restrictions.
            for statement in sqlparse.split(export_dataset(dataset, schema)):
                if sqlparse.format(statement, strip_comments=True).strip():
                    cursor.execute(statement)
            cursor.execute(f"SELECT value FROM `{sentinel}`.keep_me")
            assert cursor.fetchall() == ((42,),)
            table = "customers" if dataset == "online-store" else "stores"
            cursor.execute(f"SELECT COUNT(*) FROM `{schema}`.`{table}`")
            assert cursor.fetchone()[0] == (8 if dataset == "online-store" else 3)
            # Literal escaping survives the export's stated session mode.
            cursor.execute("SELECT " + sql_literal("O'Reilly\\folder"))
            assert cursor.fetchone()[0] == "O'Reilly\\folder"
    finally:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{schema}`")
            cursor.execute(f"DROP DATABASE IF EXISTS `{sentinel}`")
