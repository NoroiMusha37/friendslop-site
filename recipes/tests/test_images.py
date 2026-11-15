import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.urls import reverse

from recipes.models import Recipe, RecipeImage
from recipes.tests.conftest import image_file


def images_url(recipe):
    return reverse("recipe-add-images", args=[recipe.pk])


def test_admin_uploads_several_images(admin_client, recipe):
    response = admin_client.post(
        images_url(recipe), {"images": [image_file("a.png"), image_file("b.png")]}, format="multipart"
    )

    assert response.status_code == 201
    assert len(response.json()) == 2
    assert all(os.path.exists(image.image.path) for image in recipe.images.all())


def test_one_bad_file_saves_none(admin_client, recipe):
    not_an_image = SimpleUploadedFile("notes.png", b"just text", content_type="image/png")

    response = admin_client.post(
        images_url(recipe), {"images": [image_file("a.png"), not_an_image]}, format="multipart"
    )

    assert response.status_code == 400
    assert list(response.json()["images"]) == ["1"]
    assert not recipe.images.exists()


def test_failed_save_leaves_no_files(admin_client, recipe, monkeypatch, settings):
    real_save = RecipeImage.save
    calls = []

    def save_failing_on_second(self, *args, **kwargs):
        calls.append(self)
        if len(calls) == 2:
            self.image.save(self.image.name, self.image.file, save=False)  # the file is written, like a real save
            raise DatabaseError("database went away")
        return real_save(self, *args, **kwargs)

    monkeypatch.setattr(RecipeImage, "save", save_failing_on_second)

    with pytest.raises(DatabaseError):
        admin_client.post(
            images_url(recipe), {"images": [image_file("a.png"), image_file("b.png")]}, format="multipart"
        )

    assert not recipe.images.exists()
    assert not [f for _, _, files in os.walk(settings.MEDIA_ROOT) for f in files]


def test_heic_is_refused_with_clear_message(admin_client, recipe):
    heic = SimpleUploadedFile("IMG_0001.HEIC", b"\x00\x00\x00\x18ftypheic", content_type="image/heic")

    response = admin_client.post(images_url(recipe), {"images": [heic]}, format="multipart")

    assert response.status_code == 400
    assert "HEIC" in str(response.json())


def test_admin_deletes_image_of_that_recipe_only(admin_client, recipe, django_capture_on_commit_callbacks):
    image = RecipeImage.objects.create(recipe=recipe, image=image_file())
    other = Recipe.objects.create(title="Other", instructions="-", cooking_method="RAW")

    assert admin_client.delete(reverse("recipe-delete-image", args=[other.pk, image.pk])).status_code == 404
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.delete(reverse("recipe-delete-image", args=[recipe.pk, image.pk]))

    assert response.status_code == 204
    assert not os.path.exists(image.image.path)


def test_regular_user_cant_change_images(user_client, recipe):
    image = RecipeImage.objects.create(recipe=recipe, image=image_file())

    assert user_client.post(images_url(recipe), {"images": [image_file()]}, format="multipart").status_code == 403
    assert user_client.delete(reverse("recipe-delete-image", args=[recipe.pk, image.pk])).status_code == 403
