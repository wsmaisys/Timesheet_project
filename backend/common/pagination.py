"""Pagination matching SRS §12 (`{items, meta: {limit, offset, total}}`)."""

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class LimitOffsetMetaPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200
    limit_query_param = "limit"
    offset_query_param = "offset"

    def get_paginated_response(self, data):
        return Response(
            {
                "items": data,
                "meta": {
                    "limit": self.get_limit(self.request),
                    "offset": self.get_offset(self.request),
                    "total": self.count,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["items", "meta"],
            "properties": {
                "items": schema,
                "meta": {
                    "type": "object",
                    "required": ["limit", "offset", "total"],
                    "properties": {
                        "limit": {"type": "integer"},
                        "offset": {"type": "integer"},
                        "total": {"type": "integer"},
                    },
                },
            },
        }
