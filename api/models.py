from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.validators import RegexValidator, EmailValidator
from .managers import CustomUserManager
import uuid

cpf_validator = RegexValidator(
    regex=r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$',
    message='CPF deve seguir o formato 999.999.999-99.'
)

cep_validator = RegexValidator(
    regex=r'^\d{5}\-?\d{3}$',
    message='CEP deve seguir o formato 99999-999.'
)

rg_validator = RegexValidator(
    regex=r'^\d{10}\-?\d{1}$',
    message='O Registro Geral possui 11 digitos.'
)


class User(AbstractUser):
    username = None
    email = models.EmailField('endereço de e-mail', unique=True, validators=[EmailValidator()])
    USERNAME_FIELD = 'email' # Define qual campo é o identificador único para o LOGIN
    REQUIRED_FIELDS = [] 
    objects = CustomUserManager()

    def __str__(self):
        return self.email
    def delete(self, *args, **kwargs):
        # Usamos transaction.atomic para garantir que tudo aconteça ou nada aconteça.
        with transaction.atomic():
            # Verifica se existe um perfil de aluno associado e o deleta primeiro
            if hasattr(self, 'aluno'):
                self.aluno.delete()
            # O mesmo para professor
            if hasattr(self, 'professor'):
                self.professor.delete()
            
            # Chama o método delete original para deletar o usuário
            super().delete(*args, **kwargs)

class Estado(models.Model):
    id = models.BigIntegerField(primary_key=True)
    id_ibge = models.CharField(unique=True)
    nome = models.CharField(max_length=255)
    uf = models.CharField(max_length=5)
    regiao = models.CharField(max_length=50)
    pais = models.CharField(max_length=50)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'

    def __str__(self):
        return f"{self.nome}"


class Municipio(models.Model):
    id = models.BigIntegerField(primary_key=True)
    nome = models.CharField(max_length=255)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)
    codigo_ibge = models.CharField(default=0)
    capital = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.estado.uf}"


class Aluno(models.Model):
    class OrgaoExpedidor(models.TextChoices):
        SSP = 'SSP',  'SSP'
        SSPDS = 'SSPDS', 'SSPDS'
        PC = 'PC', 'PC'
        DETRAN = 'DETRAN', 'DETRAN'
        IGP = 'IGP', 'IGP'
        OUTRO = 'OUTRO', 'Outro'

    class SexoChoices(models.TextChoices):
        FEMININO = 'F', 'Feminino'
        MASCULINO = 'M', 'Masculino'
        OUTRO = 'O', 'Outro'
        PREFIRO_NAO_INFORMAR = 'N', 'Prefiro não informar'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil_aluno")
    data_nascimento=models.DateField(blank=True, null=True)
    sexo=models.CharField(max_length=1, choices=SexoChoices.choices, verbose_name="Sexo")
    cpf=models.CharField(max_length=14, unique=True, blank=True, null=True, validators=[cpf_validator])
    
    numero_identidade=models.CharField("Número do RG", max_length=20, blank=True, validators=[rg_validator])
    orgao_expedidor=models.CharField(max_length=10, choices=OrgaoExpedidor.choices, verbose_name="Órgão Expedidor")
    uf_expedidor=models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="UF de Expedição")
    
    naturalidade =models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True, related_name='nascidos_aqui', verbose_name="Cidade de Nascimento")
   
    cep=models.CharField("CEP", max_length=9, validators=[cep_validator], blank=True)
    logradouro=models.CharField("Logradouro", max_length=255, blank=True)
    numero_endereco=models.CharField("Número", max_length=20, blank=True)
    bairro=models.CharField("Bairro", max_length=100, blank=True)
    cidade=models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True, related_name='moradores', verbose_name="Cidade")
    
    telefone_celular = models.CharField("Celular", max_length=15, blank=True)
    
    class Meta:
        verbose_name = "Dados de Aluno"
        verbose_name_plural = "Dados de Alunos"
        unique_together = ('numero_identidade', 'orgao_expedidor', 'uf_expedidor')

    def __str__(self):
        return self.user.get_full_name()
    
    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()


class Professor(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE, related_name="professor")
    siape = models.CharField(max_length=20, unique=True)
    cpf = models.CharField(max_length=14, unique=True, validators=[cpf_validator])
    data_nascimento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.siape}"
    

class Curso(models.Model):
    """
    Representa um curso oferecido na plataforma.
    """
    class StatusChoices(models.TextChoices):
        AGENDADO = 'AGENDADO', 'Agendado'
        INSCRICOES_ABERTAS = 'INSCRIÇÕES ABERTAS', 'Inscrições Abertas'
        EM_ANDAMENTO = 'EM ANDAMENTO', 'Em Andamento'
        FINALIZADO = 'FINALIZADO','Finalizado'
        CANCELADO = 'CANCELADO','Cancelado'

    # --- Atributos em uma única linha ---
    nome = models.CharField(max_length=255, verbose_name="Nome do Curso")
    descricao = models.TextField(verbose_name="Descrição Completa")
    descricao_curta = models.CharField(max_length=200, verbose_name="Descrição Curta", help_text="Texto que aparecerá nos cards do curso.")
    requisitos = models.TextField(verbose_name="Requisitos do Curso", blank=True)
    carga_horaria = models.PositiveIntegerField(verbose_name="Carga Horária (em horas)")
    vagas_internas = models.PositiveIntegerField(default=20, verbose_name="Vagas para Alunos Internos")
    vagas_externas = models.PositiveIntegerField(default=10, verbose_name="Vagas para Alunos Externos")
    data_inicio_inscricoes = models.DateTimeField(verbose_name="Início das Inscrições")
    data_fim_inscricoes = models.DateTimeField(verbose_name="Fim das Inscrições")
    data_inicio_curso = models.DateField(verbose_name="Início do Curso")
    data_fim_curso = models.DateField(verbose_name="Fim do Curso")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.AGENDADO, verbose_name="Status do Curso")

    # --- Relações ---
    criador = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, related_name='cursos_criados', verbose_name="Professor Criador")
    
    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['nome']

    def __str__(self):
        return self.nome

    

class InscricaoAluno(models.Model):
    class StatusInscricao(models.TextChoices):
        AGUARDANDO_VALIDACAO = 'AGUARDANDO_VALIDACAO', 'Aguardando Validação'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        LISTA_ESPERA = 'LISTA_ESPERA', 'Lista de Espera'
        CANCELADA = 'CANCELADA', 'Cancelada'
    class TipoVaga(models.TextChoices):
        INTERNO = 'INTERNO', 'Interno'
        EXTERNO = 'EXTERNO', 'Externo'
        NI = 'NI', 'ni'
    
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=30, choices=StatusInscricao.choices, default=StatusInscricao.AGUARDANDO_VALIDACAO)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    
    tipo_vaga = models.CharField(max_length=10, choices=TipoVaga.choices)
    matricula = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        verbose_name="Matrícula(para vagas internas)"
    )
    class Meta:
        unique_together = ('aluno', 'curso')

    def __str__(self):
        return f"Inscrição de {self.aluno.user.username} em {self.curso.nome}"
    

class Documento(models.Model):
    # A ligação: Cada documento pertence a UMA inscrição.
    inscricao = models.ForeignKey(
        InscricaoAluno, 
        on_delete=models.CASCADE, 
        related_name='documentos'
    )

    # O campo que guarda o arquivo.
    # 'upload_to' diz ao Django para salvar os arquivos em uma pasta 'documentos_inscricao'
    # dentro da sua pasta de media.
    arquivo = models.FileField(upload_to='documentos_inscricao/')

    # Opcional: o nome que o arquivo tinha no computador do usuário
    nome_original = models.CharField(max_length=255, blank=True)

    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Documento para a inscrição {self.inscricao.id} - {self.nome_original}"