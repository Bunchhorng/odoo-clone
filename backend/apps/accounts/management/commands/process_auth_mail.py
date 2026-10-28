import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.accounts.recovery import cleanup_transient_records, process_next_delivery


class Command(BaseCommand):
    help = "Process queued password recovery mail; --loop polls for Docker development."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args, **options):
        iterations = 0
        while True:
            while process_next_delivery():
                pass
            if iterations % 30 == 0:
                cleanup_transient_records()
            if not options["loop"]:
                return
            close_old_connections()
            time.sleep(2)
            iterations += 1
