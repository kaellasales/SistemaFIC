#!/usr/bin/env python
"""
Script para verificar e corrigir o status dos cursos
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Curso
from django.utils import timezone

def check_courses():
    """Verificar status dos cursos"""
    print("🔍 Verificando cursos...")
    print("=" * 50)
    
    cursos = Curso.objects.all()
    
    if not cursos.exists():
        print("❌ Nenhum curso encontrado!")
        return
    
    now = timezone.now()
    
    for curso in cursos:
        print(f"\n📚 Curso: {curso.nome}")
        print(f"   Status atual: {curso.status}")
        print(f"   Início inscrições: {curso.data_inicio_inscricoes}")
        print(f"   Fim inscrições: {curso.data_fim_inscricoes}")
        print(f"   Início curso: {curso.data_inicio_curso}")
        print(f"   Fim curso: {curso.data_fim_curso}")
        
        # Verificar se está no período de inscrições
        if curso.data_inicio_inscricoes <= now <= curso.data_fim_inscricoes:
            print("   ✅ Dentro do período de inscrições")
            if curso.status != 'INSCRIÇÕES ABERTAS':
                print("   🔄 Atualizando status para 'INSCRIÇÕES ABERTAS'")
                curso.status = 'INSCRIÇÕES ABERTAS'
                curso.save()
        else:
            print("   ❌ Fora do período de inscrições")
            if now < curso.data_inicio_inscricoes:
                print("   📅 Inscrições ainda não começaram")
            elif now > curso.data_fim_inscricoes:
                print("   ⏰ Período de inscrições já terminou")
        
        print(f"   Vagas internas: {curso.vagas_internas}")
        print(f"   Vagas externas: {curso.vagas_externas}")

def main():
    print("🚀 Verificando status dos cursos...")
    check_courses()
    print("\n✅ Verificação concluída!")

if __name__ == '__main__':
    main()
