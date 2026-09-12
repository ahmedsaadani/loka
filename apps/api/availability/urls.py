from django.urls import path

from availability.views import HostCalendarViewSet

blocks = HostCalendarViewSet.as_view({"get": "blocks", "post": "blocks"})
block_detail = HostCalendarViewSet.as_view({"delete": "delete_block"})
calendars = HostCalendarViewSet.as_view({"get": "calendars", "post": "calendars"})
calendar_detail = HostCalendarViewSet.as_view(
    {"delete": "calendar_detail", "post": "calendar_detail"}
)

urlpatterns = [
    path("host/properties/<uuid:property_public_id>/blocks/", blocks, name="host-blocks"),
    path(
        "host/properties/<uuid:property_public_id>/blocks/<int:block_id>/",
        block_detail,
        name="host-block-detail",
    ),
    path("host/properties/<uuid:property_public_id>/calendars/", calendars, name="host-calendars"),
    path(
        "host/properties/<uuid:property_public_id>/calendars/<int:calendar_id>/",
        calendar_detail,
        name="host-calendar-detail",
    ),
]
