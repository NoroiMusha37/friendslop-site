from rest_framework.routers import SimpleRouter

from exercises.views import ExerciseViewSet, TrainingPlanViewSet

router = SimpleRouter()
router.register(
    "exercises",
    ExerciseViewSet,
    basename="exercise",
)
router.register(
    "plans",
    TrainingPlanViewSet,
    basename="plan",
)

urlpatterns = router.urls
