"""Provision an existing RouteOS account without exposing passwords in shell history."""
import argparse
import getpass
from contextlib import closing
from app import connection, initialize_database, password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Existing driver/admin account name")
    args = parser.parse_args()
    password = getpass.getpass("New password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 256:
        parser.error("Password must contain 12–256 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    initialize_database()
    with closing(connection()) as db, db:
        row = db.execute("SELECT id FROM users WHERE lower(name)=lower(?)", (args.name.strip(),)).fetchone()
        if row is None:
            parser.error("Account does not exist")
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(password), row["id"]))
        db.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
    print("Password provisioned; previous sessions revoked.")


if __name__ == "__main__":
    main()
