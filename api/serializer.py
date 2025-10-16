from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from api.models import(Aluno, Estado, Municipio,
Professor, CustomUserManager, Curso, InscricaoAluno, 
Documento)
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
User = get_user_model()

class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estado
        fields = ['id', 'id_ibge', 'nome', 'uf', 'regiao', 'pais', 'longitude', 'latitude']

class MunicipioSerializer(serializers.ModelSerializer):
    estado = EstadoSerializer(read_only=True)
    class Meta:
        model = Municipio
        fields = ['id', 'nome', 'estado']
        
class PasswordResetRequestSerializer(serializers.Serializer):
    """Recebe o e-mail para iniciar processo de reset de senha."""

    email = serializers.EmailField()

    class Meta:
        fields = ('email',)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirma o reset de senha com uid, token e nova senha."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    """Serializer para o CCA definir uma nova senha para um usuário."""
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "As senhas não coincidem."})
    
        validate_password(data['new_password'])
        
        return data
    
class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para a troca de senha. Valida a senha antiga e confirma a nova.
    """
    old_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Sua senha antiga não está correta.")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "As senhas não coincidem."})
        # Você pode adicionar validações de força de senha aqui
        return data

    def save(self, **kwargs):
        password = self.validated_data['new_password']
        user = self.context['request'].user
        user.set_password(password)
        user.save()
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """Atualização parcial de dados do usuário (sem alterar e-mail)."""

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        read_only_fields = ('email',)
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }


class UserSerializer(serializers.ModelSerializer):
    """Serializer de criação de usuário com senha."""
    perfil_completo = serializers.SerializerMethodField()

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    
    groups = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'groups', 'perfil_completo']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
    def get_perfil_completo(self, obj):
        # A verificação é SÓ esta. Existe a relação com o perfil de aluno?
        return hasattr(obj, 'perfil_aluno')

class AlunoRegistroSerializer(UserSerializer):
    """Cria usuário e atribui automaticamente a role 'ALUNO'."""

    def create(self, validated_data):
        user = super().create(validated_data)
        grupo_aluno, _ = Group.objects.get_or_create(name="ALUNO")
        user.groups.add(grupo_aluno)
        return user


class AlunoPerfilSerializer(serializers.ModelSerializer):
    """
    Gerencia a CRIAÇÃO e ATUALIZAÇÃO do perfil de um aluno.
    """

    # 🔹 Para leitura (GET): mostra nome e id
    uf_expedidor = EstadoSerializer(read_only=True)
    naturalidade = MunicipioSerializer(read_only=True)
    cidade = MunicipioSerializer(read_only=True)

    # 🔹 Para escrita (POST/PUT): permite enviar só os IDs
    uf_expedidor_id = serializers.PrimaryKeyRelatedField(
        queryset=Estado.objects.all(),
        source='uf_expedidor',
        write_only=True,
        required=False
    )
    naturalidade_id = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.all(),
        source='naturalidade',
        write_only=True,
        required=False
    )
    cidade_id = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.all(),
        source='cidade',
        write_only=True,
        required=False
    )

    class Meta:
        model = Aluno
        fields = (
            'data_nascimento', 'sexo', 'cpf', 'numero_identidade',
            'orgao_expedidor', 'uf_expedidor', 'uf_expedidor_id',
            'naturalidade', 'naturalidade_id', 'cep',
            'logradouro', 'numero_endereco', 'bairro',
            'cidade', 'cidade_id', 'telefone_celular',
        )
        

    def update(self, instance, validated_data):
        """
        Este método lida com a atualização TANTO do perfil do Aluno
        QUANTO dos dados aninhados do User.
        """
        # 1. Pega os dados do usuário do payload
        user_data = validated_data.pop('user', {})
        
        # 2. Atualiza os campos do User aninhado usando o serializer especialista
        #    'partial=True' é importante para permitir atualizações parciais
        user_serializer = UserUpdateSerializer(instance.user, data=user_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        # 3. Deixa o DRF fazer o resto do trabalho de atualizar os campos do Aluno
        return super().update(instance, validated_data)

class AlunoReadOnlySerializer(serializers.ModelSerializer):
    """
    Serializer de LEITURA para o perfil do Aluno.
    Mostra todos os detalhes, incluindo o objeto 'user' completo.
    """
    user = UserSerializer(read_only=True)
    
    cidade = MunicipioSerializer(read_only=True)
    naturalidade = MunicipioSerializer(read_only=True)
    uf_expedidor = EstadoSerializer(read_only=True)

    class Meta:
        model = Aluno
        fields = [
            'id', 'user', 'data_nascimento', 'sexo', 'cpf', 'numero_identidade',
            'orgao_expedidor', 'uf_expedidor', 'naturalidade', 'cep',
            'logradouro', 'numero_endereco', 'bairro', 'cidade', 'telefone_celular',
        ]
class CursoBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['id', 'nome', 'status']
        

class ProfessorSerializer(serializers.ModelSerializer):
    user = UserSerializer() # Aninha o UserSerializer para leitura e escrita
    total_courses = serializers.SerializerMethodField()
    cursos_criados = CursoBasicSerializer(many=True, read_only=True)

    class Meta:
        model = Professor
        fields = ['id', 'user', 'siape', 'cpf', 'data_nascimento', 'total_courses', 'cursos_criados']
        read_only_fields = ['id']

    def get_total_courses(self, obj):
        """
        Esta função é chamada automaticamente para preencher o campo 'total_courses'.
        'obj' aqui é a instância do Professor.
        """
        # Ele conta quantos cursos têm este professor como 'criador'
        return obj.cursos_criados.count()
    

    def create(self, validated_data):
        """
        Lida com a criação aninhada do Professor e do User.
        """
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        
        user = User.objects.create_user(**user_data, password=password)
        
        grupo_professor, _ = Group.objects.get_or_create(name="PROFESSOR")
        user.groups.add(grupo_professor)
        
        professor = Professor.objects.create(user=user, **validated_data)
        return professor

    def update(self, instance, validated_data):
        """
        Lida com a atualização aninhada do Professor e do User.
        Esta é a versão mais limpa e idiomática.
        """
        user_data = validated_data.pop('user', {})
        
        # 1. Atualiza os campos do Professor (DRF faz isso automaticamente)
        instance = super().update(instance, validated_data)

        # 2. Atualiza os campos do User aninhado de forma segura
        user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
        if user_serializer.is_valid(raise_exception=True):
            user_serializer.save()
            
        return instance


class CursoSerializer(serializers.ModelSerializer):
    criador = ProfessorSerializer(read_only=True)

    class Meta:
        model = Curso
        fields = [
            'id', 'nome', 'descricao', 'descricao_curta', 'requisitos',
            'carga_horaria', 'vagas_internas', 'vagas_externas',
            'data_inicio_inscricoes', 'data_fim_inscricoes',
            'data_inicio_curso', 'data_fim_curso',
            'status', 
            'criador',
        ]
        read_only_fields = ['id', 'criador', 'status']

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'email']

class AlunoBasicSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    class Meta:
        model = Aluno
        fields = ['id', 'user']


class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = ['id', 'arquivo', 'nome_original', 'data_upload']

class InscricaoAlunoSerializer(serializers.ModelSerializer):
    aluno = AlunoBasicSerializer(read_only=True)
    curso = CursoBasicSerializer(read_only=True)
    documentos = DocumentoSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # --- Campos de ESCRITA (para o frontend enviar) ---
    curso_id = serializers.PrimaryKeyRelatedField(
        queryset=Curso.objects.all(), source='curso', write_only=True
    )
    tipo_vaga = serializers.ChoiceField(choices=InscricaoAluno.TipoVaga.choices, write_only=True)
    
    arquivos_upload = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        write_only=True, required=False
    )
    matricula = serializers.CharField(max_length=50, required=False, write_only=True)

    class Meta:
        model = InscricaoAluno
        fields = [
            'id', 'aluno', 'curso', 'status', 'status_display', 'data_inscricao', 'documentos',
            'curso_id', 'matricula','tipo_vaga', 'arquivos_upload'
        ]
        read_only_fields = ['aluno', 'status']

    def validate(self, data):
        """
        Este método é o "fiscal". Ele roda antes de qualquer tentativa de salvar.
        É o lugar perfeito para as suas validações de negócio.
        """
        aluno = self.context['request'].user.perfil_aluno
        curso = data.get('curso')
        tipo_vaga = data.get('tipo_vaga')
        matricula = data.get('matricula')

        # Se for vaga interna, a matrícula é OBRIGATÓRIA
        if tipo_vaga == 'INTERNO' and not matricula:
            raise serializers.ValidationError({'matricula': 'Este campo é obrigatório para vagas internas.'})
        
        # 1. Validação de duplicação
        if InscricaoAluno.objects.filter(aluno=aluno, curso=curso).exists():
            raise serializers.ValidationError('Você já solicitou inscrição neste curso.')

        # 2. Validação de vagas (com transação para segurança)
        with transaction.atomic():
            curso_locked = Curso.objects.select_for_update().get(id=curso.id)
            vagas_totais = curso_locked.vagas_internas if tipo_vaga == 'INTERNO' else curso_locked.vagas_externas
            inscricoes_confirmadas = InscricaoAluno.objects.filter(
                curso=curso_locked, tipo_vaga=tipo_vaga, status='CONFIRMADA'
            ).count()
            if inscricoes_confirmadas >= vagas_totais:
                raise serializers.ValidationError('Não há mais vagas disponíveis para este tipo.')
        
        return data

    def create(self, validated_data):
        """
        Cria a Inscrição e depois os Documentos associados.
        """
        arquivos = validated_data.pop('arquivos_upload', [])
        
        # Cria a Inscrição com os dados já validados.
        # 'aluno' será injetado pelo perform_create da ViewSet.
        inscricao = super().create(validated_data)
        
        # Cria os objetos Documento para cada arquivo enviado
        for arquivo in arquivos:
            Documento.objects.create(inscricao=inscricao, arquivo=arquivo, nome_original=arquivo.name)
            
        return inscricao