from __future__ import annotations

import importlib.util
from typing import Any

from sqlalchemy.engine import URL


DRIVER_PACKAGES = {
    "PostgreSQL": ("psycopg", 'python -m pip install "psycopg[binary]"'),
    "MySQL": ("pymysql", "python -m pip install PyMySQL"),
    "MariaDB": ("pymysql", "python -m pip install PyMySQL"),
    "Microsoft SQL Server": ("pyodbc", "python -m pip install pyodbc"),
    "Oracle": ("oracledb", "python -m pip install oracledb"),
}


def python_driver_available(platform: str) -> bool:
    if platform not in DRIVER_PACKAGES:
        return True
    return importlib.util.find_spec(DRIVER_PACKAGES[platform][0]) is not None


def install_command(platform: str) -> str | None:
    item = DRIVER_PACKAGES.get(platform)
    return item[1] if item else None


def installed_odbc_drivers() -> list[str]:
    try:
        import pyodbc
        return list(pyodbc.drivers())
    except Exception:
        return []


def build_database_url(platform: str, values: dict[str, Any]) -> str:
    if platform == "SQLite":
        path = str(values.get("path", "geophysical_platform.db")).strip()
        if not path:
            raise ValueError("SQLite database file path is required.")
        if path.startswith("sqlite:///"):
            return path
        return f"sqlite:///{path}"

    if platform == "PostgreSQL":
        return URL.create(
            "postgresql+psycopg",
            username=values["username"], password=values["password"],
            host=values["host"], port=int(values["port"]), database=values["database"],
        ).render_as_string(hide_password=False)

    if platform in {"MySQL", "MariaDB"}:
        dialect = "mysql+pymysql" if platform == "MySQL" else "mariadb+pymysql"
        return URL.create(
            dialect,
            username=values["username"], password=values["password"],
            host=values["host"], port=int(values["port"]), database=values["database"],
        ).render_as_string(hide_password=False)

    if platform == "Microsoft SQL Server":
        driver = str(values.get("odbc_driver", "")).strip()
        host = str(values.get("host", "")).strip()
        database = str(values.get("database", "")).strip()
        if not driver:
            raise ValueError("An installed SQL Server ODBC driver must be selected.")
        if not host:
            raise ValueError("SQL Server host is required.")
        if not database:
            raise ValueError("SQL Server database name is required.")

        query = {
            "driver": driver,
            "Encrypt": "yes" if values.get("encrypt", True) else "no",
            "TrustServerCertificate": "yes" if values.get("trust_server_certificate", True) else "no",
        }
        # For named instances (SERVER\INSTANCE), the ODBC driver resolves the
        # instance. Do not also force a port, which can cause confusing connection
        # failures. Otherwise use the explicitly supplied TCP port.
        named_instance = bool(values.get("named_instance")) or "\\" in host
        port = None if named_instance else int(values.get("port", 1433))

        if values.get("authentication") == "Windows Integrated":
            query["Trusted_Connection"] = "yes"
            return URL.create(
                "mssql+pyodbc", host=host, port=port, database=database, query=query,
            ).render_as_string(hide_password=False)
        username = str(values.get("username", "")).strip()
        if not username:
            raise ValueError("SQL Server username is required for SQL Server Authentication.")
        return URL.create(
            "mssql+pyodbc", username=username, password=values.get("password", ""),
            host=host, port=port, database=database, query=query,
        ).render_as_string(hide_password=False)

    if platform == "Oracle":
        return URL.create(
            "oracle+oracledb", username=values["username"], password=values["password"],
            host=values["host"], port=int(values["port"]),
            query={"service_name": values["service_name"]},
        ).render_as_string(hide_password=False)

    raise ValueError(f"Unsupported database platform: {platform}")
