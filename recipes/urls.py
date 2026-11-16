from rest_framework.routers import SimpleRouter

from recipes.views import IngredientViewSet, RecipeViewSet

router = SimpleRouter()
router.register(
    "recipes",
    RecipeViewSet,
    basename="recipe",
)
router.register(
    "ingredients",
    IngredientViewSet,
    basename="ingredient",
)

urlpatterns = router.urls
