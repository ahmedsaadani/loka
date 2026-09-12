from django.urls import path
from rest_framework.routers import SimpleRouter

from geo.views import CityViewSet, NeighborhoodDetailView, NeighborhoodListView

router = SimpleRouter()
router.register("cities", CityViewSet, basename="city")
router.register("neighborhoods", NeighborhoodListView, basename="neighborhood")

urlpatterns = [
    path(
        "cities/<slug:city_slug>/neighborhoods/<slug:slug>/",
        NeighborhoodDetailView.as_view(),
        name="neighborhood-detail",
    ),
    *router.urls,
]
