"""
URL configuration for config project.

Define rotas e endpoints para a API do SistemaFIC, incluindo autenticação,
perfil de usuário, CRUD de professores e documentação Swagger/Redoc.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions, routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from api.views import (
    AlunoRegistroView, AlunoPerfilView, ChangePasswordView,
    PasswordResetConfirmView, PasswordResetRequestView, LogoutView,
    ProfessorViewSet, UserViewSet, CursoViewSet,
    InscricaoAlunoViewSet, MeView
    
)

# --- Configuração do Swagger/OpenAPI ---
schema_view = get_schema_view(
    openapi.Info(
        title="SistemaFIC",
        default_version="v1",
        description="""
            API do backend do Sistema de Inscrição em Cursos (FIC).
            
            Funcionalidades principais:
            - Gerenciamento de autenticação e perfis de usuários (Alunos, Professores, Admins)
            - Criação, listagem e detalhamento de cursos
            - Sistema de inscrição de alunos em cursos
            - Controle de acesso baseado em papéis (RBAC)
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="kaellasales09@gmail.com"),
        license=openapi.License(name="BSD License"),
        public=True,
        security_definitions={
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Adicione o token JWT com o prefixo "Bearer ". Exemplo: "Bearer eyJhbGciOiJI..."'
                }
            },
        security=[{'Bearer': []}]
        )
)   

# --- Router para ViewSets ---
router = routers.DefaultRouter()
router.register(r'professor', ProfessorViewSet, basename='Professor')
router.register(r'usuario', UserViewSet, basename="User")
router.register(r'cursos', CursoViewSet)
router.register(r'inscricoes-aluno', InscricaoAlunoViewSet, basename='inscricao-aluno')

# --- URLs principais ---
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),

    # Autenticação JWT
    path('token/', TokenObtainPairView.as_view(), name='login'), # <--- INTEGRADA AO FRONT
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Perfis e usuários
    path('perfil/aluno/', AlunoPerfilView.as_view(), name='perfil-aluno'),
    path("me/", MeView.as_view(), name="me"),
    path('registro/aluno/', AlunoRegistroView.as_view(), name='aluno-registro'), # <--- INTEGRADA AO FRONT
    path('usuario/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('usuario/reset-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('usuario/reset-password-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),

    # Documentação
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# --- Servindo arquivos estáticos em modo DEBUG ---
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
