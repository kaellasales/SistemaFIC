from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Municipio, Estado, Aluno, CustomUserManager, Role


@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    """Admin para modelo Estado."""
    list_display = ('nome', 'uf', 'id_ibge')
    search_fields = ('nome', 'uf')


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    """Admin para modelo Município."""
    list_display = ('nome', 'estado', 'codigo_ibge')
    search_fields = ('nome', 'codigo_ibge')
    list_filter = ('estado', 'capital')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin customizado para o modelo User sem username."""
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    # Campos exibidos na edição
    fieldsets = (
        (None, {'fields': ('email', 'password', 'first_name', 'last_name')}),
        ('Permissões', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Datas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    # Campos exibidos no formulário de criação
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    """Admin para modelo Aluno."""
    list_display = ('user', 'cpf', 'data_nascimento', 'telefone_celular')
    search_fields = ('user__username', 'user__email', 'cpf')
    list_filter = ('sexo', 'naturalidade', 'cidade')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin para modelo Aluno."""
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']