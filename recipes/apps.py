from django.apps import AppConfig


class RecipesConfig(AppConfig):
    name = "recipes"

    def ready(self):
        import recipes.signals  # noqa: F401  (connects the file-deletion handlers)
