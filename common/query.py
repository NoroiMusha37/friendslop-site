from pydantic import BaseModel, ValidationError
from rest_framework import serializers


def parse_query[T: BaseModel](schema: type[T], request) -> T:
    """The request's query parameters checked by `schema`; errors become DRF's usual 400: `{"size": ["..."]}`."""
    try:
        return schema.model_validate(request.query_params.dict())
    except ValidationError as e:
        errors = {}
        for error in e.errors():
            field = str(error["loc"][0]) if error["loc"] else "non_field_errors"
            errors.setdefault(field, []).append(error["msg"])
        raise serializers.ValidationError(errors) from e
