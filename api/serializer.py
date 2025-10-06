from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from api.models import(Aluno, Estado, Municipio,
Professor, CustomUserManager, Curso, InscricaoAluno)
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
User = get_user_model()

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
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'groups']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AlunoRegistroSerializer(UserSerializer):
    """Cria usuário e atribui automaticamente a role 'ALUNO'."""

    def create(self, validated_data):
        user = super().create(validated_data)
        grupo_aluno, _ = Group.objects.get_or_create(name="ALUNO")
        user.groups.add(grupo_aluno)
        return user


class AlunoPerfilSerializer(serializers.ModelSerializer):
    """Gerencia o perfil de um aluno vinculado ao usuário logado."""

    user = UserUpdateSerializer(required=False, allow_null=True)

    class Meta:
        model = Aluno
        fields = (
            'user',
            'data_nascimento', 'sexo', 'cpf',
            'numero_identidade', 'orgao_expedidor', 'uf_expedidor',
            'naturalidade', 'cep', 'logradouro', 'numero_endereco',
            'bairro', 'cidade', 'telefone_celular',
        )

    def create(self, validated_data):
        """Cria perfil de aluno e atualiza dados básicos do usuário."""
        user_data = validated_data.pop('user', {})
        user = self.context['request'].user

        if isinstance(user_data, dict):
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.save()

        return Aluno.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        """Atualiza perfil de aluno e dados básicos do usuário."""
        user_data = validated_data.pop('user', {})
        user = instance.user

        if isinstance(user_data, dict):
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.save()

        return super().update(instance, validated_data)


class ProfessorSerializer(serializers.ModelSerializer):
    user = UserSerializer() # Aninha o UserSerializer para leitura e escrita

    class Meta:
        model = Professor
        fields = ['id', 'user', 'siape', 'cpf', 'data_nascimento']
        read_only_fields = ['id']

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


class CursoBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['id', 'nome']


class InscricaoAlunoSerializer(serializers.ModelSerializer):
    aluno = AlunoBasicSerializer(read_only=True)
    curso = CursoBasicSerializer(read_only=True)
    
    # Usamos um 'SerializerMethodField' para mostrar o texto do status, não só o código
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InscricaoAluno
        fields = [
            'id',
            'aluno',
            'curso',
            'status',
            'status_display', # Campo extra para o frontend
            'tipo_vaga',
            'data_inscricao'
        ]
        read_only_fields = ['status', 'aluno']