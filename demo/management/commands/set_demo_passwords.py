"""Set one local password for the synthetic demo-* users. Nothing is stored in the repo."""

import sys
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

MIN_LENGTH = 8


class Command(BaseCommand):
    help = "Set a password for every demo-* user (prompted, or read from stdin)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password-stdin", action="store_true", help="Read the password from stdin."
        )

    def handle(self, *args, password_stdin=False, **options):
        users = list(get_user_model().objects.filter(username__startswith="demo-"))
        if not users:
            raise CommandError("No demo-* users; run seed_demo first")
        if password_stdin:
            password = sys.stdin.readline().rstrip("\n")
        else:
            password = getpass("Demo password: ")
            if getpass("Again: ") != password:
                raise CommandError("Passwords do not match")
        if len(password) < MIN_LENGTH:
            raise CommandError(f"Password must be at least {MIN_LENGTH} characters")
        for user in users:
            user.set_password(password)
            user.save(update_fields=["password"])
        names = ", ".join(sorted(u.username for u in users))
        self.stdout.write(self.style.SUCCESS(f"Password set for {names}"))
