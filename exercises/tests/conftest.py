import pytest
from django.utils import timezone

from exercises.tests.helpers import make_exercise


@pytest.fixture
def exercise(db):
    return make_exercise()


@pytest.fixture
def archived(db):
    return make_exercise("Old curl", archived_at=timezone.now())
