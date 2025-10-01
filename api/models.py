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

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Ex: 'ADMIN', 'PROFESSOR', 'ALUNO'

    def __str__(self):
        return self.name

class User(AbstractUser):
    username = None
    email = models.EmailField('endereço de e-mail', unique=True, validators=[EmailValidator()])
    USERNAME_FIELD = 'email' # Define qual campo é o identificador único para o LOGIN
    REQUIRED_FIELDS = [] 
    objects = CustomUserManager()
    roles = models.ManyToManyField(Role, blank=True, related_name="users")

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
    id=models.BigAutoField(primary_key=True)
    nome=models.CharField(max_length=255, blank=False, null=False)
    carga_horaria=models.IntegerField(blank=False, null=False)
    descricao=models.TextField(blank=False)
    criador=models.ForeignKey(Professor, on_delete=models.CASCADE)
    professores=models.ManyToManyField(Professor, through='Convite', related_name="cursos_lecionados")
    vagas_internas = models.PositiveIntegerField(
        default=0, 
        help_text="Número de vagas para alunos internos."
    )
    vagas_externas = models.PositiveIntegerField(
        default=0,
        help_text="Número de vagas para alunos externos."
    )
    def __str__(self):
        return self.nome
    

class Convite(models.Model):
    class StatusConvite(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ACEITO = 'ACEITO', 'Aceito'
        RECUSADO = 'RECUSADO', 'Recusado'

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=10, choices=StatusConvite.choices, default=StatusConvite.PENDENTE)
    
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    data_envio = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('curso', 'professor') # Um professor só pode ser convidado uma vez para o mesmo curso

    def __str__(self):
        return f"Convite para {self.professor} no curso {self.curso.nome} ({self.status})"
    


class InscricaoAluno(models.Model):
    class StatusInscricao(models.TextChoices):
        AGUARDANDO_VALIDACAO = 'AGUARDANDO_VALIDACAO', 'Aguardando Validação'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        LISTA_ESPERA = 'LISTA_ESPERA', 'Lista de Espera'
        CANCELADA = 'CANCELADA', 'Cancelada'

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=30, choices=StatusInscricao.choices, default=StatusInscricao.AGUARDANDO_VALIDACAO)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    
    tipo_vaga = models.CharField(max_length=10, choices=(('INTERNO', 'Interno'), ('EXTERNO', 'Externo')))
    class Meta:
        unique_together = ('aluno', 'curso')

    def __str__(self):
        return f"Inscrição de {self.aluno.user.username} em {self.curso.nome}"