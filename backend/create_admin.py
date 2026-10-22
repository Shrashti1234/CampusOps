"""Create a local CampusOps admin. Run from backend directory.

Usage: python create_admin.py admin@example.edu
Password is prompted securely; never pass it as a command-line argument.
"""
from getpass import getpass
import sys
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from main import Base, engine, Session, User, password_hash

if __name__ == "__main__":
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        raise SystemExit("Usage: python create_admin.py admin@example.edu")
    email = sys.argv[1].strip().lower()
    password = getpass("New admin password (at least 10 characters): ")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters")
    Base.metadata.create_all(engine)
    with Session() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists. Choose another email.")
        user = User(id=str(uuid4()), email=email, password_hash=password_hash.hash(password), role="admin", created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
    print("Admin account created.")
