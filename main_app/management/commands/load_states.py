# main_app/management/commands/load_states.py
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings

# Get the model dynamically (replace 'State' if your model is named differently)
State = apps.get_model('main_app', 'State')


class Command(BaseCommand):
    help = 'Loads state data from the State.txt file into the database.'

    def handle(self, *args, **options):
        # 1. Determine file path (assumes State.txt is in the project root)
        file_path = os.path.join(settings.BASE_DIR, 'State.txt')

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"State.txt file not found at {file_path}"))
            return

        # 2. Read the file content
        with open(file_path, 'r') as f:
            state_names = [line.strip() for line in f if line.strip()]

        # 3. Insert the data
        created_count = 0
        self.stdout.write("Starting data load...")

        for name in state_names:
            # Check if state already exists to prevent duplicates
            obj, created = State.objects.get_or_create(
                name=name
                # If your model has other required fields (like 'slug' or 'code'),
                # you must add logic here to generate them.
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {created_count} new states.'))