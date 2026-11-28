from rest_framework import status
from rest_framework.exceptions import APIException


class ExerciseArchived(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This exercise is archived. Restore it first."
    default_code = "exercise_archived"
