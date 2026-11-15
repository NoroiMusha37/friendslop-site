from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from recipes.models import Recipe, RecipeImage


def delete_file_after_commit(file):
    """Removes a stored file once the database change is committed, so a failed save never loses a file."""
    if file:
        storage, name = file.storage, file.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(post_delete, sender=Recipe)
def delete_recipe_cover(sender, instance, **kwargs):
    delete_file_after_commit(instance.cover_image)


@receiver(post_delete, sender=RecipeImage)
def delete_gallery_image(sender, instance, **kwargs):
    delete_file_after_commit(instance.image)
