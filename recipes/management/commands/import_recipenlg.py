from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from recipes.recipenlg import import_recipenlg


class Command(BaseCommand):
    help = "Import ingredients and ingredient pair scores from the RecipeNLG CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)

    def handle(self, *args, csv_path, **options):
        if not csv_path.is_file():
            raise CommandError(f"File not found: {csv_path}")
        self.stdout.write("Reading the CSV, this takes a few minutes...")
        result = import_recipenlg(csv_path)
        self.stdout.write(
            self.style.SUCCESS(
                f"{result['recipes']} recipes read: "
                f"{result['ingredients']} ingredients, {result['pairs']} pairs stored.",
            ),
        )
