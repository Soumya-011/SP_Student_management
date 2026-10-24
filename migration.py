"""
migration.py — Run this ONCE before starting the app for the first time,
and again whenever the database schema changes.

Usage:
    python migration.py

What it does:
    1. Connects as the superuser (DB_USER / DB_PASSWORD from .env).
    2. Creates the coaching_migrator role (DDL — owns the schema).
    3. Creates the coaching_app role (DML only — used by FastAPI at runtime).
    4. Grants each role the correct privileges.
    5. Reconnects as coaching_migrator and runs Base.metadata.create_all()
       to create all application tables.

Credentials are read entirely from .env — no passwords are hardcoded here.
Required .env variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD   ← superuser
    MIGRATOR_DB_USER, MIGRATOR_DB_PASSWORD             ← DDL role
    APP_DB_USER, APP_DB_PASSWORD                       ← DML role
"""

import sys
import textwrap

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Load settings (reads .env automatically via pydantic-settings)
# ---------------------------------------------------------------------------
from app.core.config import settings
from app.models import Base  # noqa: F401 — side-effect: registers all ORM models

# ---------------------------------------------------------------------------
# Resolve role names and passwords from .env
# ---------------------------------------------------------------------------
MIGRATOR_USER = settings.MIGRATOR_DB_USER
MIGRATOR_PASS = settings.MIGRATOR_DB_PASSWORD
APP_USER      = settings.APP_DB_USER
APP_PASS      = settings.APP_DB_PASSWORD
DB_NAME       = settings.DB_NAME

_missing = [
    name for name, val in [
        ("MIGRATOR_DB_USER", MIGRATOR_USER),
        ("MIGRATOR_DB_PASSWORD", MIGRATOR_PASS),
        ("APP_DB_USER", APP_USER),
        ("APP_DB_PASSWORD", APP_PASS),
    ]
    if not val
]
if _missing:
    print(
        f"\n[ERROR] The following variables are missing from .env:\n"
        + "\n".join(f"  • {v}" for v in _missing)
        + "\n\nAdd them and re-run migration.py.\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")

def _info(msg: str) -> None:
    print(f"  ->  {msg}")

def _section(title: str) -> None:
    print(f"\n{'-' * 55}")
    print(f"  {title}")
    print(f"{'-' * 55}")


# ---------------------------------------------------------------------------
# Step 1 — Connect as superuser and provision roles / privileges
# ---------------------------------------------------------------------------
_section("Step 1 — Provisioning roles (connecting as superuser)")
_info(f"Superuser : {settings.DB_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{DB_NAME}")

try:
    # psycopg2 is used for raw DDL statements that SQLAlchemy cannot run
    # in a transaction (e.g. CREATE ROLE, GRANT ON DATABASE).
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
except Exception as exc:
    print(f"\n[ERROR] Could not connect as superuser: {exc}\n")
    sys.exit(1)

# -- Create coaching_migrator if it does not exist ----------------------------
cur.execute(
    "SELECT 1 FROM pg_roles WHERE rolname = %s", (MIGRATOR_USER,)
)
if cur.fetchone():
    _ok(f"Role '{MIGRATOR_USER}' already exists — skipping creation.")
else:
    cur.execute(
        f"CREATE ROLE {MIGRATOR_USER} LOGIN PASSWORD %s", (MIGRATOR_PASS,)
    )
    _ok(f"Role '{MIGRATOR_USER}' created.")

# -- Update migrator password (idempotent) ------------------------------------
cur.execute(f"ALTER ROLE {MIGRATOR_USER} PASSWORD %s", (MIGRATOR_PASS,))
_ok(f"Password set for '{MIGRATOR_USER}'.")

# -- Create coaching_app if it does not exist ---------------------------------
cur.execute(
    "SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_USER,)
)
if cur.fetchone():
    _ok(f"Role '{APP_USER}' already exists — skipping creation.")
else:
    cur.execute(
        f"CREATE ROLE {APP_USER} LOGIN PASSWORD %s", (APP_PASS,)
    )
    _ok(f"Role '{APP_USER}' created.")

# -- Update app password (idempotent) -----------------------------------------
cur.execute(f"ALTER ROLE {APP_USER} PASSWORD %s", (APP_PASS,))
_ok(f"Password set for '{APP_USER}'.")

# -- Database-level CONNECT privileges ----------------------------------------
cur.execute(f"GRANT CONNECT ON DATABASE {DB_NAME} TO {MIGRATOR_USER}")
cur.execute(f"GRANT CONNECT ON DATABASE {DB_NAME} TO {APP_USER}")
_ok(f"CONNECT on database '{DB_NAME}' granted to both roles.")

# -- Schema-level privileges ---------------------------------------------------
cur.execute(f"GRANT ALL ON SCHEMA public TO {MIGRATOR_USER}")
cur.execute(f"GRANT USAGE ON SCHEMA public TO {APP_USER}")
_ok(f"Schema 'public' — ALL granted to migrator, USAGE granted to app role.")

# -- DML on all existing tables / sequences -> coaching_app -------------------
cur.execute(
    f"GRANT SELECT, INSERT, UPDATE, DELETE "
    f"ON ALL TABLES IN SCHEMA public TO {APP_USER}"
)
cur.execute(
    f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_USER}"
)
_ok(f"DML (SELECT/INSERT/UPDATE/DELETE) on existing tables granted to '{APP_USER}'.")

# -- DEFAULT PRIVILEGES so coaching_app gets DML on all FUTURE tables too ----
cur.execute(
    f"ALTER DEFAULT PRIVILEGES FOR ROLE {MIGRATOR_USER} IN SCHEMA public "
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_USER}"
)
cur.execute(
    f"ALTER DEFAULT PRIVILEGES FOR ROLE {MIGRATOR_USER} IN SCHEMA public "
    f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_USER}"
)
_ok(f"Default privileges set — future tables by '{MIGRATOR_USER}' will auto-grant DML to '{APP_USER}'.")

cur.close()
conn.close()


# ---------------------------------------------------------------------------
# Step 2 — Reconnect as coaching_migrator and create all tables
# ---------------------------------------------------------------------------
_section("Step 2 — Creating tables (connecting as coaching_migrator)")
_info(f"Migrator  : {MIGRATOR_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{DB_NAME}")

try:
    migrator_engine = create_engine(
        settings.migrator_database_url,
        pool_pre_ping=True,
    )
    # Verify the connection before touching the schema
    with migrator_engine.connect() as probe:
        probe.execute(text("SELECT 1"))

    Base.metadata.create_all(bind=migrator_engine)
    _ok("Base.metadata.create_all() completed — all tables are up to date.")
    migrator_engine.dispose()
except Exception as exc:
    print(f"\n[ERROR] Table creation failed: {exc}\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
_section("Migration complete")
print(textwrap.dedent(f"""
  Roles created / updated:
    • {MIGRATOR_USER}  — DDL only (CREATE / ALTER tables)
    • {APP_USER}       — DML only (SELECT / INSERT / UPDATE / DELETE)

  The FastAPI app will now connect as '{APP_USER}'.
  Never use the superuser '{settings.DB_USER}' to run the app.

  Next step:
    uvicorn app.main:app --reload
"""))
