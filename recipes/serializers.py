from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Comment, Favorite, Rating
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    ingredient_id = serializers.IntegerField(
        source='ingredient.id', read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'ingredient', 'ingredient_id', 'amount')


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author', 'text', 'created_at', 'updated_at')
        read_only_fields = ('author', 'created_at', 'updated_at')


class RecipeListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    avg_rating = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'title', 'description', 'tags',
            'time_minutes', 'created_at', 'updated_at',
            'avg_rating', 'is_favorited', 'comments_count'
        )

    def get_avg_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings:
            return sum(r.value for r in ratings) / len(ratings)
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_comments_count(self, obj):
        return obj.comments.count()


class IngredientInputSerializer(serializers.Serializer):
    ingredient = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=5, decimal_places=2)


class RecipeDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), source='tags', many=True, write_only=True
    )
    recipe_ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    ingredients_data = IngredientInputSerializer(many=True, write_only=True, required=False)
    comments = CommentSerializer(many=True, read_only=True)
    avg_rating = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'title', 'description', 'tags', 'tag_ids',
            'steps', 'time_minutes', 'created_at', 'updated_at',
            'recipe_ingredients', 'ingredients_data', 'comments',
            'avg_rating', 'is_favorited', 'comments_count'
        )
        read_only_fields = ('author', 'created_at', 'updated_at')

    def get_avg_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings:
            return sum(r.value for r in ratings) / len(ratings)
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_comments_count(self, obj):
        return obj.comments.count()

    def validate(self, data):
        # Check tags
        tags = data.get('tags', [])
        if not tags or len(tags) == 0:
            raise serializers.ValidationError("At least one tag is required")
        
        ingredients_data = data.get('ingredients_data')
        if not ingredients_data or len(ingredients_data) == 0:
            raise serializers.ValidationError("At least one ingredient is required")
        
        # Check for duplicate ingredients
        ingredient_ids = [ing.get('ingredient') for ing in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Duplicate ingredients are not allowed")
        
        # Validate each ingredient
        for ing_data in ingredients_data:
            amount = ing_data.get('amount')
            if not amount or float(amount) < 0.1:
                raise serializers.ValidationError("Amount must be at least 0.1")
            
            # Check if ingredient exists
            ingredient_id = ing_data.get('ingredient')
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(f"Ingredient with id {ingredient_id} does not exist")
        
        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients_data', [])
        recipe = Recipe.objects.create(**validated_data)
        
        if tags:
            recipe.tags.set(tags)

        for ing_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ing_data['ingredient'],
                amount=ing_data['amount']
            )

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients_data', None)

        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.steps = validated_data.get('steps', instance.steps)
        instance.time_minutes = validated_data.get('time_minutes', instance.time_minutes)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ing_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=ing_data['ingredient'],
                    amount=ing_data['amount']
                )

        return instance


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ('id', 'value')


class ShoppingListSerializer(serializers.Serializer):
    recipe_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated")

        recipe_ids = validated_data.get('recipe_ids')
        
        if recipe_ids:
            recipes = Recipe.objects.filter(id__in=recipe_ids)
        else:
            recipes = Recipe.objects.filter(favorites__user=request.user)

        ingredients = {}
        for recipe in recipes:
            for recipe_ing in recipe.recipe_ingredients.all():
                key = (recipe_ing.ingredient.name, recipe_ing.ingredient.unit)
                if key in ingredients:
                    ingredients[key] += recipe_ing.amount
                else:
                    ingredients[key] = recipe_ing.amount

        return ingredients
