"""Small JSON API helpers; authentication uses Django sessions and CSRF."""
import json
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse


class APIError(Exception):
    def __init__(self, message, status=400, *, headers=None):
        self.message = message
        self.status = status
        self.headers = headers or {}


def api(methods, *, authenticated=True):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                if request.method not in methods:
                    response = JsonResponse({"error": "Method not allowed."}, status=405)
                    response["Allow"] = ", ".join(methods)
                elif authenticated and not request.user.is_authenticated:
                    response = JsonResponse({"error": "Please sign in."}, status=401)
                else:
                    response = view(request, *args, **kwargs)
            except APIError as exc:
                response = JsonResponse({"error": exc.message}, status=exc.status)
                for key, value in exc.headers.items():
                    response[key] = value
            except ValidationError as exc:
                response = JsonResponse({"error": " ".join(exc.messages)}, status=400)
            except IntegrityError:
                response = JsonResponse({"error": "This record already exists. Refresh and try again."}, status=409)
            response["Cache-Control"] = "private, no-store"
            return response
        return wrapped
    return decorate


def json_body(request, allowed):
    if request.content_type != "application/json":
        raise APIError("Send an application/json request.", 415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise APIError("The request must contain valid JSON.") from None
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise APIError("The request contains unsupported fields.")
    return data


def text_field(data, key, *, maximum, required=True):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise APIError(f"{key.replace('_', ' ').capitalize()} must be text.")
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise APIError(f"{key.replace('_', ' ').capitalize()} must contain 1 to {maximum} characters.")
    return value


def csrf_failure(request, reason=""):
    return JsonResponse({"error": "Your security token expired. Refresh the page and try again."}, status=403)
