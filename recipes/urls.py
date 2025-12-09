from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TagViewSet, IngredientViewSet, RecipeViewSet, CommentViewSet
)

router = DefaultRouter()
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]
