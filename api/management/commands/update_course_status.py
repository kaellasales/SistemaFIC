from django.core.management.base import BaseCommand
from django.utils import timezone
from seu_app.models import Curso # Importe seu modelo Curso

class Command(BaseCommand):
    help = 'Verifica e atualiza o status dos cursos com base nas datas atuais'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        self.stdout.write(f"[{now.strftime('%Y-%m-%d %H:%M')}] Iniciando verificação de status dos cursos...")

        # --- LÓGICA 1: De AGENDADO para INSCRIÇÕES ABERTAS ---
        cursos_para_abrir = Curso.objects.filter(
            status=Curso.StatusChoices.AGENDADO,
            data_inicio_inscricoes__lte=now
        )
        count_abertos = cursos_para_abrir.update(status=Curso.StatusChoices.INSCricoes_ABERTAS)
        if count_abertos:
            self.stdout.write(self.style.SUCCESS(f'  -> {count_abertos} curso(s) tiveram suas inscrições abertas.'))

        # --- LÓGICA 2: De INSCRIÇÕES ABERTAS para EM ANDAMENTO ---
        # Um curso começa quando sua data de início chega E as inscrições já estavam abertas.
        cursos_para_iniciar = Curso.objects.filter(
            status=Curso.StatusChoices.INSCricoes_ABERTAS,
            data_inicio_curso__lte=today
        )
        count_iniciados = cursos_para_iniciar.update(status=Curso.StatusChoices.EM_ANDAMENTO)
        if count_iniciados:
            self.stdout.write(self.style.SUCCESS(f'  -> {count_iniciados} curso(s) entraram em andamento.'))
            
        # --- LÓGICA 3: De EM ANDAMENTO para FINALIZADO ---
        cursos_para_finalizar = Curso.objects.filter(
            status=Curso.StatusChoices.EM_ANDAMENTO,
            data_fim_curso__lt=today
        )
        count_finalizados = cursos_para_finalizar.update(status=Curso.StatusChoices.FINALIZADO)
        if count_finalizados:
            self.stdout.write(self.style.SUCCESS(f'  -> {count_finalizados} curso(s) foram finalizados.'))

        self.stdout.write("Verificação concluída.")