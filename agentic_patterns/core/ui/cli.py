"""CLI for managing users."""

import argparse
import sys

from agentic_patterns.core.config.config import USER_DATABASE_FILE
from agentic_patterns.core.ui.auth import UserDatabase, generate_password


def main():
    parser = argparse.ArgumentParser(description="Manage users")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add user
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("username", help="Username")
    add_parser.add_argument(
        "--password", "-p", help="Password (generated if not provided)"
    )
    add_parser.add_argument("--role", "-r", default="user", help="Role (default: user)")

    # Delete user
    del_parser = subparsers.add_parser("delete", help="Delete a user")
    del_parser.add_argument("username", help="Username to delete")

    # List users
    subparsers.add_parser("list", help="List all users")

    # Change password
    passwd_parser = subparsers.add_parser("passwd", help="Change user password")
    passwd_parser.add_argument("username", help="Username")
    passwd_parser.add_argument(
        "--password", "-p", help="New password (generated if not provided)"
    )

    args = parser.parse_args()
    db = UserDatabase(USER_DATABASE_FILE)

    if args.command == "add":
        password = args.password or generate_password()
        if db.add_user(args.username, password, args.role):
            print(f"User '{args.username}' added with role '{args.role}'")
            if not args.password:
                print(f"Generated password: {password}")
        else:
            print(f"User '{args.username}' already exists", file=sys.stderr)
            sys.exit(1)

    elif args.command == "delete":
        if db.delete_user(args.username):
            print(f"User '{args.username}' deleted")
        else:
            print(f"User '{args.username}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        users = db.list_users()
        if users:
            for username in users:
                user = db.get_user(username)
                print(f"{username} ({user.role})")
        else:
            print("No users")

    elif args.command == "passwd":
        user = db.get_user(args.username)
        if not user:
            print(f"User '{args.username}' not found", file=sys.stderr)
            sys.exit(1)
        password = args.password or generate_password()
        # Direct password update (bypasses old password check)
        users = db._load_users()
        users[args.username].password_hash = db._hash_password(password)
        db._save_users(users)
        print(f"Password changed for '{args.username}'")
        if not args.password:
            print(f"Generated password: {password}")


if __name__ == "__main__":
    main()
