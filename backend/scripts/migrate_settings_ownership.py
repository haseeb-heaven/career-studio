"""One-time migration for legacy global settings rows.

Run from the backend directory before restarting the deployed server:
    python scripts/migrate_settings_ownership.py
"""
from pathlib import Path
import sys

from sqlmodel import Session, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import engine  # noqa: E402
from models import Settings, User  # noqa: E402


def main() -> None:
    with Session(engine) as session:
        legacy_rows = session.exec(select(Settings).where(Settings.user_id == None)).all()  # noqa: E711
        if not legacy_rows:
            print("No legacy settings rows found.")
            return

        first_user = session.exec(select(User).order_by(User.id)).first()
        if not first_user:
            deleted = len(legacy_rows)
            for row in legacy_rows:
                session.delete(row)
            session.commit()
            print(f"Deleted {deleted} legacy settings row(s); no users exist.")
            return

        existing = session.exec(select(Settings).where(Settings.user_id == first_user.id)).first()
        assigned = 0
        deleted = 0

        if existing:
            rows_to_delete = legacy_rows
        else:
            keeper, *rows_to_delete = legacy_rows
            keeper.user_id = first_user.id
            session.add(keeper)
            assigned = 1

        for row in rows_to_delete:
            session.delete(row)
            deleted += 1

        session.commit()
        print(
            "Settings ownership migration complete: "
            f"assigned={assigned}, deleted={deleted}, admin_user_id={first_user.id}"
        )


if __name__ == "__main__":
    main()
