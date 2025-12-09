from rest_framework.permissions import BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """
    Позволяет редактирование только автору,
    остальным - только чтение
    """

    def has_object_permission(self, request, view, obj):
        # Чтение разрешено всем
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Редактирование/удаление только для автора
        return obj.author == request.user
