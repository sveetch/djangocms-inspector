import datetime
import json
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError

from ...creator import PageCreator

class Command(BaseCommand):
    help = (
        "TEMPORARY on development for PageCreator"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            type=Path,
            default=[],
            required=False,
            help=(
                "Path to a JSON manifest for pages and their content to create."
            )
        )

    def print(self, content=""):
        """
        Print content to stdout if silent mode is disabled.
        """
        if not self.silent:
            self.stdout.write(content)

    def handle(self, *args, **options):
        print("TODO!")
