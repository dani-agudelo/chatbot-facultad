"""Script: crear tablas y sembrar el primer administrador."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin.db import Base, SessionLocal, engine  # noqa: E402
from admin.models import AdminUser  # noqa: E402
from admin.security import hash_password  # noqa: E402
from admin.services import get_or_create_settings  # noqa: E402
from admin.settings import get_admin_settings  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_admin_settings()
    db = SessionLocal()
    try:
        get_or_create_settings(db)
        existing = (
            db.query(AdminUser)
            .filter(AdminUser.email == settings.admin_email.lower().strip())
            .first()
        )
        if existing is None:
            user = AdminUser(
                email=settings.admin_email.lower().strip(),
                password_hash=hash_password(settings.admin_password),
                full_name=settings.admin_full_name,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Admin creado: {user.email}")
        else:
            print(f"Admin ya existe: {existing.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
