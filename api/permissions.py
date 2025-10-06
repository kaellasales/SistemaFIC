from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsAdminUser(BasePermission):
    " Permite acesso apenas a usuários autenticados e que sejam administradores."
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
    
class IsCCAUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="CCA").exists()
    
class IsProfessorUser(permissions.BasePermission):
    """Permite acesso apenas a usuários que tenham um perfil de Professor."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'professor')

class IsProfessorOrCCAUser(permissions.BasePermission):
    """Permite acesso a usuários dos grupos 'PROFESSOR' ou 'CCA'."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Aqui, como estamos checando múltiplos grupos, a verificação de grupos é ideal.
        return request.user.groups.filter(name__in=['PROFESSOR', 'CCA']).exists()
    
class IsAlunoUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'aluno')