from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from .managers import CustomUserManager


cpf_validator = RegexValidator(
    regex=r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$',
    message='CPF deve seguir o formato 999.999.999-99.'
)

cep_validator = RegexValidator(
    regex=r'^\d{5}-\d{3}$',
    message='CEP deve seguir o formato 99999-999.'
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
    cpf=models.CharField(max_length=14, unique=True, blank=True, null=True, validators=[cpf_validator]) # CPF pode ser nulo
    
    numero_identidade=models.CharField("Número do RG", max_length=20, blank=True)
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


class Professor(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil_professor")
    siape = models.CharField(max_length=20, unique=True)
    cpf = models.CharField(max_length=14, unique=True, validators=[cpf_validator])
    data_nascimento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.siape}"