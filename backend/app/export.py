"""Export only the public, deterministic practice fixture as inspectable SQL."""
from datetime import date, datetime
from decimal import Decimal
import math
import re

from .content.datasets import DATASETS

SQL_MODE = "STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION,ONLY_FULL_GROUP_BY"


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite seed numbers are not supported.")
        return repr(value)
    if isinstance(value, datetime):
        value = value.isoformat(sep=" ")
    elif isinstance(value, date):
        value = value.isoformat()
    if not isinstance(value, str):
        raise ValueError("Unsupported public seed value.")
    # The export sets a known session SQL mode before these literals execute.
    return "'" + value.replace("\\", "\\\\").replace("'", "''").replace("\x00", "\\0") + "'"


class SeedRecorder:
    def __init__(self):
        self.statements = []

    def execute(self, sql, args=None):
        if args is not None:
            sql = sql % tuple(sql_literal(value) for value in args)
        self.statements.append(sql.rstrip("; \n") + ";")

    def executemany(self, sql, rows):
        for row in rows:
            self.execute(sql, row)


def export_dataset(dataset: str, schema_name: str | None = None) -> str:
    if dataset not in DATASETS:
        raise ValueError("Unknown dataset.")
    schema_name = schema_name or f"querylab_{dataset.replace('-', '_')}_v1"
    if not re.fullmatch(r"querylab_[a-z0-9_]{1,55}", schema_name):
        raise ValueError("Use a QueryLab-specific database name.")
    authored = DATASETS[dataset]
    recorder = SeedRecorder()
    authored["seed"](recorder, 0)  # Never export hidden fixture variants.
    lines = [
        "-- QueryLab public practice dataset, version 1.",
        f"-- Dataset: {authored['name']}. Requires MySQL 8.4.",
        "-- Inspect this script before importing it with your own MySQL client.",
        "-- Creates a NEW QueryLab database; contains no DROP or user/grant operations.",
        "-- Stop on errors. If the named database already exists, use a fresh name",
        "-- rather than continuing after CREATE DATABASE fails.",
        f"CREATE DATABASE `{schema_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        f"USE `{schema_name}`;",
        "SET NAMES utf8mb4;",
        "SET SESSION time_zone = '+00:00';",
        f"SET SESSION sql_mode = '{SQL_MODE}';",
        "",
        *[ddl + " ENGINE=InnoDB;" for ddl in authored["ddl"]],
        "",
        "START TRANSACTION;",
        *recorder.statements,
        "COMMIT;",
        "",
        "-- This is public practice data only. Automatic grading uses separate",
        "-- temporary fixtures managed locally by the paired QueryLab helper.",
    ]
    return "\n".join(lines) + "\n"
