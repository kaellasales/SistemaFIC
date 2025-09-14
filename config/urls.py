"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from rest_framework import permissions, routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from api.views import (
    AlunoRegistroView, AlunoPerfilView, ChangePasswordView, 
    PasswordResetConfirmView, PasswordResetRequestView, LogoutView,
    ProfessorViewSet
)

schema_view = get_schema_view(
    openapi.Info(
            title="SistemaFIC",
            default_version="v1",
            description="""
                API para o backend do Sistema de Inscrição em Cursos (FIC). Fornece endpoints para gerenciar o ciclo de vida de usuários, cursos e suas respectivas inscrições.

                **Principais Funcionalidades:**
                - Gerenciamento de autenticação e perfis de usuários (Alunos, Professores, Administradores).
                - Criação, listagem e detalhamento de cursos.
                - Sistema de inscrição de alunos em cursos.
                - Controle de acesso baseado em papéis (RBAC) para garantir a segurança dos endpoints.
                """,
            terms_of_service="https://www.google.com/policies/terms/",
            contact=openapi.Contact(email="kaellasales092gmail.com"),
            license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'professor', ProfessorViewSet, basename='Professor')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/', TokenObtainPairView.as_view(), name='login'),
    path('perfil/aluno/', AlunoPerfilView.as_view(), name='perfil-aluno'),
    path('registro/aluno/', AlunoRegistroView.as_view(), name='aluno-registro'),
    path('usuario/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('usuario/reset-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('usuario/reset-password-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)