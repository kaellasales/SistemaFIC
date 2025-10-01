from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsAdminUser(BasePermission):
    " Permite acesso apenas a usuários autenticados e que sejam administradores."
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
    


class IsProfessorUser(permissions.BasePermission):
    """
    Permite acesso apenas a usuários autenticados que tenham um perfil de professor.
    """
    def has_permission(self, request, view):
        # O usuário precisa estar logado E ter o atributo 'professor' (a relação OneToOne)
        return request.user and request.user.is_authenticated and hasattr(request.user, 'PROFESSOR')
    
class IsAlunoUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'aluno')