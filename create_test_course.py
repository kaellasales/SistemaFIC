#!/usr/bin/env python
"""
Script para criar um curso de teste para o sistema MatriFIC
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Curso, Professor

def create_test_course():
    """Criar um curso de teste"""
    
    # Buscar o professor criado
    try:
        professor = Professor.objects.first()
        if not professor:
            print("❌ Nenhum professor encontrado. Execute primeiro o create_test_users.py")
            return
    except Exception as e:
        print(f"❌ Erro ao buscar professor: {e}")
        return
    
    # Verificar se já existe um curso de teste
    if Curso.objects.filter(nome__icontains='Curso de Teste').exists():
        print("ℹ️  Curso de teste já existe")
        return
    
    # Datas para o curso
    hoje = datetime.now()
    inicio_inscricoes = hoje - timedelta(days=1)  # Inscrições começaram ontem
    fim_inscricoes = hoje + timedelta(days=30)    # Inscrições terminam em 30 dias
    inicio_curso = hoje + timedelta(days=45)      # Curso começa em 45 dias
    fim_curso = hoje + timedelta(days=75)         # Curso termina em 75 dias
    
    curso = Curso.objects.create(
        nome='Curso de Teste - Programação Web',
        descricao='Curso introdutório de programação web com HTML, CSS e JavaScript. Ideal para iniciantes que desejam aprender a criar sites modernos e responsivos.',
        descricao_curta='Aprenda programação web do zero!',
        requisitos='Conhecimento básico de informática. Não é necessário experiência prévia em programação.',
        carga_horaria=40,
        vagas_internas=20,
        vagas_externas=10,
        data_inicio_inscricoes=inicio_inscricoes,
        data_fim_inscricoes=fim_inscricoes,
        data_inicio_curso=inicio_curso,
        data_fim_curso=fim_curso,
        status='INSCRIÇÕES ABERTAS',
        criador=professor
    )
    
    print("✅ Curso de teste criado com sucesso!")
    print(f"   Nome: {curso.nome}")
    print(f"   Carga Horária: {curso.carga_horaria} horas")
    print(f"   Vagas Internas: {curso.vagas_internas}")
    print(f"   Vagas Externas: {curso.vagas_externas}")
    print(f"   Inscrições até: {curso.data_fim_inscricoes.strftime('%d/%m/%Y')}")
    print(f"   Início do curso: {curso.data_inicio_curso.strftime('%d/%m/%Y')}")
    print(f"   Status: {curso.status}")

def main():
    print("🚀 Criando curso de teste para o MatriFIC...")
    print("=" * 50)
    
    try:
        create_test_course()
        print()
        print("=" * 50)
        print("✅ Ambiente de teste configurado!")
        print()
        print("🎯 PRÓXIMOS PASSOS:")
        print("1. Inicie o frontend: cd SistemaFICFront/frontend && npm run dev")
        print("2. Acesse: http://localhost:3000")
        print("3. Faça login como aluno: aluno@fic.com / aluno123")
        print("4. Vá para a página de cursos")
        print("5. Teste a inscrição no curso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar curso: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
