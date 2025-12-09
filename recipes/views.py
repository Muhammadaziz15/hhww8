from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import (
    Tag, Ingredient, Recipe, Comment, Rating, Favorite, RecipeIngredient
)
from .serializers import (
    TagSerializer, IngredientSerializer, RecipeListSerializer,
    RecipeDetailSerializer, CommentSerializer, RatingSerializer,
    ShoppingListSerializer
)
from .permissions import IsAuthorOrReadOnly


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title']
    ordering_fields = ['time_minutes', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['list']:
            return RecipeListSerializer
        return RecipeDetailSerializer

    def get_queryset(self):
        queryset = Recipe.objects.prefetch_related(
            'author', 'tags', 'recipe_ingredients', 'comments', 'ratings', 'favorites'
        )
        
        # Filter by author
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        # Filter favorited
        favorited = self.request.query_params.get('favorited')
        if favorited and self.request.user.is_authenticated:
            queryset = queryset.filter(favorites__user=self.request.user)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        return [AllowAny()]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'detail': 'Already in favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )

        Favorite.objects.create(user=user, recipe=recipe)
        return Response(status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def unfavorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        favorite = get_object_or_404(Favorite, user=user, recipe=recipe)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def rating(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            value = request.data.get('value')
            
            if not value or int(value) < 1 or int(value) > 5:
                return Response(
                    {'detail': 'Value must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            rating, created = Rating.objects.get_or_create(
                user=user, recipe=recipe,
                defaults={'value': int(value)}
            )
            
            if not created:
                rating.value = int(value)
                rating.save()
            
            serializer = RatingSerializer(rating)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        elif request.method == 'DELETE':
            rating = get_object_or_404(Rating, user=user, recipe=recipe)
            rating.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def shopping_list(self, request):
        serializer = ShoppingListSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            ingredients = serializer.save()
            return Response(ingredients, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        recipe_id = self.kwargs.get('recipe_id')
        if recipe_id:
            return Comment.objects.filter(recipe_id=recipe_id)
        return Comment.objects.all()
