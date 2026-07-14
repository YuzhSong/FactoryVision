from uuid import uuid4

from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_response(*, code=200, message="success", data=None, request_id=None, status=200):
    payload = {
        "code": code,
        "message": message,
        "data": data,
        "requestId": request_id or str(uuid4()),
    }
    return Response(payload, status=status)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        # DRF 的 detail 有时是 dict 有时是 list 有时是 string
        if isinstance(detail, dict):
            detail = str(detail.get("detail", list(detail.values())[0] if detail else ""))
        elif isinstance(detail, list):
            detail = str(detail[0])
        else:
            detail = str(detail)

        response.data = {
            "code": response.status_code,
            "message": detail,
            "data": None,
            "requestId": str(uuid4()),
        }
    return response
