from django.contrib import admin
from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Comment, Favorite, Rating
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'unit')
    search_fields = ('name',)
    list_filter = ('unit',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'time_minutes', 'created_at')
    search_fields = ('title', 'author__username')
    list_filter = ('tags', 'created_at')
    filter_horizontal = ('tags',)
    inlines = [RecipeIngredientInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'author', 'created_at')
    search_fields = ('text', 'author__username', 'recipe__title')
    list_filter = ('created_at',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__title')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'value')
    search_fields = ('user__username', 'recipe__title')
    list_filter = ('value',)
