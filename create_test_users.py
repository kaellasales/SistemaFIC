#!/usr/bin/env python
"""
Script para criar usuários de teste para o sistema MatriFIC
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from api.models import Aluno, Professor

User = get_user_model()

def create_groups():
    """Criar grupos de usuários se não existirem"""
    groups = ['ALUNO', 'PROFESSOR', 'CCA']
    for group_name in groups:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ Grupo '{group_name}' criado")
        else:
            print(f"ℹ️  Grupo '{group_name}' já existe")

def create_admin():
    """Criar usuário administrador"""
    email = 'admin@fic.com'
    password = 'admin123'
    
    if User.objects.filter(email=email).exists():
        print(f"ℹ️  Administrador '{email}' já existe")
        return User.objects.get(email=email)
    
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Administrador',
        last_name='Sistema'
    )
    
    # Adicionar ao grupo CCA
    cca_group = Group.objects.get(name='CCA')
    user.groups.add(cca_group)
    
    print(f"✅ Administrador criado: {email} / {password}")
    return user

def create_professor():
    """Criar usuário professor"""
    email = 'professor@fic.com'
    password = 'prof123'
    
    if User.objects.filter(email=email).exists():
        print(f"ℹ️  Professor '{email}' já existe")
        return User.objects.get(email=email)
    
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name='João',
        last_name='Silva'
    )
    
    # Adicionar ao grupo PROFESSOR
    professor_group = Group.objects.get(name='PROFESSOR')
    user.groups.add(professor_group)
    
    # Criar perfil de professor
    professor = Professor.objects.create(
        user=user,
        siape='1234567',
        cpf='123.456.789-00',
        data_nascimento='1980-01-01'
    )
    
    print(f"✅ Professor criado: {email} / {password}")
    print(f"   SIAPE: {professor.siape}")
    return user

def create_aluno():
    """Criar usuário aluno"""
    email = 'aluno@fic.com'
    password = 'aluno123'
    
    if User.objects.filter(email=email).exists():
        print(f"ℹ️  Aluno '{email}' já existe")
        return User.objects.get(email=email)
    
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name='Maria',
        last_name='Santos'
    )
    
    # Adicionar ao grupo ALUNO
    aluno_group = Group.objects.get(name='ALUNO')
    user.groups.add(aluno_group)
    
    # Criar perfil de aluno
    aluno = Aluno.objects.create(
        user=user,
        data_nascimento='1995-05-15',
        sexo='F',
        cpf='987.654.321-00',
        numero_identidade='1234567890',
        orgao_expedidor='SSP',
        cep='60000-000',
        logradouro='Rua das Flores, 123',
        numero_endereco='123',
        bairro='Centro',
        telefone_celular='(85) 99999-9999'
    )
    
    print(f"✅ Aluno criado: {email} / {password}")
    print(f"   CPF: {aluno.cpf}")
    return user

def main():
    print("🚀 Criando usuários de teste para o MatriFIC...")
    print("=" * 50)
    
    try:
        # Criar grupos
        create_groups()
        print()
        
        # Criar usuários
        admin = create_admin()
        print()
        
        professor = create_professor()
        print()
        
        aluno = create_aluno()
        print()
        
        print("=" * 50)
        print("✅ Todos os usuários foram criados com sucesso!")
        print()
        print("📋 CREDENCIAIS DE TESTE:")
        print("┌─────────────────┬─────────────────┬──────────────┐")
        print("│ Tipo            │ Email           │ Senha        │")
        print("├─────────────────┼─────────────────┼──────────────┤")
        print("│ Administrador   │ admin@fic.com   │ admin123     │")
        print("│ Professor       │ professor@fic.com│ prof123      │")
        print("│ Aluno           │ aluno@fic.com   │ aluno123     │")
        print("└─────────────────┴─────────────────┴──────────────┘")
        print()
        print("🔗 URLs para testar:")
        print("• Frontend: http://localhost:3000")
        print("• Backend API: http://localhost:8080")
        print("• Admin Django: http://localhost:8080/admin/")
        print("• Swagger: http://localhost:8080/swagger/")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuários: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
