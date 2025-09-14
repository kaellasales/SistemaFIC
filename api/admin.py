from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    User, Municipio, Estado, Aluno
)


@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'id_ibge')
    search_fields = ('nome', 'uf')

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'estado', 'codigo_ibge')
    search_fields = ('nome', 'codigo_ibge')
    list_filter = ('estado', 'capital')


admin.site.register(User)
admin.site.register(Aluno)