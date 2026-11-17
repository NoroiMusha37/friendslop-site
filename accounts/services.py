import logging

from django.utils import timezone

from accounts.models import User

logger = logging.getLogger(__name__)


class UserStateError(Exception):
    """The action isn't allowed for the user's current status."""


def approve(user: User, by: User) -> None:
    if user.status != "pending":
        raise UserStateError("Only pending users can be approved.")
    user.approved_at = timezone.now()
    user.is_active = True
    user.save(update_fields=["approved_at", "is_active"])
    logger.info("%s approved %s", by.username, user.username)


def reject(user: User, by: User) -> None:
    if user.status != "pending":
        raise UserStateError("Only pending users can be rejected.")
    user.delete()
    logger.info("%s rejected (deleted) %s", by.username, user.username)


def ban(user: User, by: User) -> None:
    if user.is_superuser:
        raise UserStateError("Admins can't be banned.")
    if user.status != "active":
        raise UserStateError("Only active users can be banned.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    logger.info("%s banned %s", by.username, user.username)


def unban(user: User, by: User) -> None:
    if user.status != "banned":
        raise UserStateError("Only banned users can be unbanned.")
    user.is_active = True
    user.save(update_fields=["is_active"])
    logger.info("%s unbanned %s", by.username, user.username)
