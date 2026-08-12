"""
Snowflake connection helper for the capstone.

Covers the three connection paths from Week 4 Day 5 so you are not rebuilding
them under sprint pressure. Copy this into your team repository and adapt it.

Credentials come from a `snow.cfg` next to this file, same format as Week 4:

    [DEV]
    account =
    user =
    password =
    role =
    warehouse =
    database = TECHCATALYST
    schema =

Never commit snow.cfg. Add it to your team repo's .gitignore on day one.
"""

from configparser import ConfigParser
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "snow.cfg"
PROFILE = "DEV"


def load_params(config_path=CONFIG_PATH, profile=PROFILE):
    """Read connection parameters from snow.cfg."""
    config = ConfigParser()
    if not config.read(config_path):
        raise FileNotFoundError(
            f"No config found at {config_path}. "
            "Copy snow.cfg.template to snow.cfg and fill it in."
        )
    return dict(config[profile])


# ---------------------------------------------------------------------------
# Option 1: Python connector. Use for DDL, COPY INTO, and loading DataFrames.
# ---------------------------------------------------------------------------

def get_connection():
    """Return a raw Snowflake connection."""
    from snowflake import connector

    return connector.connect(**load_params())


def run_sql(sql, conn=None):
    """Execute one statement and return all rows."""
    close_after = conn is None
    conn = conn or get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if close_after:
            conn.close()


def query_to_df(sql, conn=None):
    """Execute a query and return a pandas DataFrame with real column names."""
    import pandas as pd

    close_after = conn is None
    conn = conn or get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)
    finally:
        if close_after:
            conn.close()


def load_dataframe(df, table_name, overwrite=False, create=True, conn=None):
    """
    Write a pandas DataFrame to a Snowflake table via write_pandas.

    Good for lookup tables and modest result sets. Do NOT use this to load
    40 million rows of trip data. For the raw files, use an external stage
    and COPY INTO, which is far faster and is what you learned in Week 4.
    """
    from snowflake.connector.pandas_tools import write_pandas

    close_after = conn is None
    conn = conn or get_connection()
    try:
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name=table_name.upper(),
            auto_create_table=create,
            overwrite=overwrite,
        )
        print(f"{table_name}: success={success} chunks={nchunks} rows={nrows}")
        return nrows
    finally:
        if close_after:
            conn.close()


# ---------------------------------------------------------------------------
# Option 2: SQLAlchemy engine. Use with pandas.read_sql and BI-style tooling.
# ---------------------------------------------------------------------------

def get_engine():
    """Return a SQLAlchemy engine for Snowflake."""
    from snowflake.sqlalchemy import URL
    from sqlalchemy import create_engine

    return create_engine(URL(**load_params()))


# ---------------------------------------------------------------------------
# Option 3: Snowpark session. Use for DataFrame-style work pushed into Snowflake.
# ---------------------------------------------------------------------------

def get_session():
    """Return a Snowpark session."""
    from snowflake.snowpark import Session

    return Session.builder.configs(load_params()).create()


# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------

def whoami():
    """Confirm the connection works and show the active context."""
    rows = run_sql(
        "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
        "CURRENT_DATABASE(), CURRENT_SCHEMA()"
    )
    user, role, warehouse, database, schema = rows[0]
    print(f"user      {user}")
    print(f"role      {role}")
    print(f"warehouse {warehouse}")
    print(f"database  {database}")
    print(f"schema    {schema}")
    return rows[0]


if __name__ == "__main__":
    whoami()
