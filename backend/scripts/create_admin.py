import argparse
import getpass

from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.models import UserRole
from app.auth.schemas import RegisterRequest
from app.auth.service import register_user
from app.core.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin account.")
    parser.add_argument("--name", required=True, help="Full name of the admin")
    parser.add_argument("--email", required=True, help="Login email of the admin")
    parser.add_argument("--phone", required=True, help="Phone number, 10 to 15 digits with optional leading +")
    args = parser.parse_args()

    # Read interactively so the password never appears in shell history or the process list.
    password = getpass.getpass("Admin password: ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Admin not created: the two passwords do not match")

    try:
        request = RegisterRequest(full_name=args.name, email=args.email, phone=args.phone, password=password)
    except ValidationError as error:
        raise SystemExit(f"Admin not created: invalid details\n{error}")

    with SessionLocal() as db:
        try:
            user = register_user(db, request, role=UserRole.ADMIN)
        except HTTPException as error:
            raise SystemExit(f"Admin not created: {error.detail}")
        print(f"Created admin {user.email} with id {user.id}")


if __name__ == "__main__":
    main()
