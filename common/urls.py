from django.urls import path

from common.views import RefreshLinksView

urlpatterns = [
    path(
        "links/refresh/",
        RefreshLinksView.as_view(),
        name="refresh-links",
    ),
]
