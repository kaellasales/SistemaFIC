from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions, routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView  


from api.views import (
    AlunoRegistroView, AlunoPerfilView, ChangePasswordView,
    PasswordResetConfirmView, PasswordResetRequestView, LogoutView,
    ProfessorViewSet, UserViewSet, CursoViewSet,
    InscricaoAlunoViewSet, MeView, FormOptionsView,
    MunicipioViewSet, EstadoView, AlunoViewSet
)

router = routers.DefaultRouter()
router.register(r'professor', ProfessorViewSet, basename='Professor')
router.register(r'usuario', UserViewSet, basename="User")
router.register(r'cursos', CursoViewSet, basename="Curso")
router.register(r'inscricoes-aluno', InscricaoAlunoViewSet, basename='inscricao-aluno')
router.register(r'municipios', MunicipioViewSet, basename="Municipio")
router.register(r'alunos', AlunoViewSet, basename='aluno')

# --- URLs da API (documentadas) ---
api_urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),

    # Autenticação JWT
    path('token/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Perfis e usuários
    path('aluno/me/', AlunoPerfilView.as_view(), name='perfil-aluno'),
    path('form-options/aluno-perfil/', FormOptionsView.as_view(), name='form-options-aluno-perfil'),
    path("me/", MeView.as_view(), name="me"),
    path('registro/aluno/', AlunoRegistroView.as_view(), name='aluno-registro'),
    path('usuario/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('usuario/reset-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('usuario/reset-password-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('estados/', EstadoView.as_view(), name='estados')
]

# --- Documentação com DRF Spectacular ---
urlpatterns = api_urlpatterns + [
    # Schema JSON
    path('schema/', SpectacularAPIView.as_view(), name='schema'),

    # Documentação Swagger e Redoc
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
# --- Servindo arquivos estáticos em modo DEBUG ---
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)