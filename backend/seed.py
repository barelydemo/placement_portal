"""Database bootstrap script.

Creates every table programmatically (SQLAlchemy models -> db.create_all()) and
seeds the single Admin superuser. Safe to run repeatedly: a second run never
creates a duplicate admin.

Run with:  python -m backend.seed
"""

from sqlalchemy import inspect, text

from backend.app import create_app
from backend.config import Config
from backend.models import User, UserRole, db


def create_tables() -> None:
    db.create_all()
    tables = sorted(db.metadata.tables.keys())
    print(f"[seed] Database file : {Config.DATABASE_PATH}")
    print(f"[seed] Tables ensured: {', '.join(tables)}")


def ensure_schema() -> None:
    """Add columns that models gained after their table was first created.

    `db.create_all()` only creates missing *tables*, never missing *columns*, so
    an existing placement.db would break when a later phase adds a field. Only
    nullable columns can be added safely in one statement — anything else is
    reported instead of guessed at.
    """
    inspector = inspect(db.engine)
    added = 0
    for table_name, table in db.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not column.nullable and column.default is None and column.server_default is None:
                print(
                    f"[schema] MANUAL STEP NEEDED: {table_name}.{column.name} is NOT NULL "
                    "with no default — cannot be added automatically."
                )
                continue
            column_type = column.type.compile(dialect=db.engine.dialect)
            db.session.execute(
                text(f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {column_type}')
            )
            print(f"[schema] Added column {table_name}.{column.name} ({column_type})")
            added += 1
    if added:
        db.session.commit()
    print(f"[schema] Schema up to date ({added} column(s) added).")


def seed_admin() -> User:
    """Create the one and only Admin user if it does not exist yet."""
    admin = db.session.query(User).filter_by(role=UserRole.ADMIN).first()
    if admin:
        print(f"[seed] Admin already present -> {admin.email} (no changes made)")
        return admin

    admin = User(
        name=Config.ADMIN_NAME,
        email=Config.ADMIN_EMAIL,
        role=UserRole.ADMIN,
        is_active=True,
    )
    admin.set_password(Config.ADMIN_PASSWORD)
    db.session.add(admin)
    db.session.commit()
    print(f"[seed] Admin created  -> {admin.email}")
    return admin


def verify() -> None:
    """Query the DB back so the result is provable without any DB browser."""
    admins = db.session.query(User).filter_by(role=UserRole.ADMIN).all()
    total_users = db.session.query(User).count()
    print("[verify] Admin rows  :", len(admins))
    print("[verify] Total users :", total_users)
    for admin in admins:
        print("[verify] Admin row   :", admin.to_dict())
    if len(admins) != 1:
        raise SystemExit(f"[verify] FAILED: expected exactly 1 admin, found {len(admins)}")
    print("[verify] OK: exactly one Admin user exists.")


def main() -> None:
    app = create_app()
    with app.app_context():
        create_tables()
        ensure_schema()
        seed_admin()
        verify()


if __name__ == "__main__":
    main()
