from uuid import uuid4

from rest_framework.response import Response


def api_response(*, code=0, message="success", data=None, request_id=None, status=200):
    payload = {
        "code": code,
        "message": message,
        "data": data,
        "requestId": request_id or str(uuid4()),
    }
    return Response(payload, status=status)
