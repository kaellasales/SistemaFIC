from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from api.models import Aluno, Estado, Municipio, Role, Professor

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """Serializer básico para roles de usuário."""

    class Meta:
        model = Role
        fields = ('name',)


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

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AlunoRegistroSerializer(UserSerializer):
    """Cria usuário e atribui automaticamente a role 'ALUNO'."""

    def create(self, validated_data):
        user = super().create(validated_data)
        aluno_role, _ = Role.objects.get_or_create(name="ALUNO")
        user.roles.add(aluno_role)
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
    """Cria professor e atribui automaticamente a role 'PROFESSOR'."""

    user = UserSerializer()

    class Meta:
        model = Professor
        fields = ['id', 'user', 'siape', 'cpf', 'data_nascimento']

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        professor = Professor.objects.create(user=user, **validated_data)

        professor_role, _ = Role.objects.get_or_create(name="PROFESSOR")
        user.roles.add(professor_role)

        return professor


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


class ChangePasswordSerializer(serializers.Serializer):
    """Troca de senha com validação da senha antiga."""

    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Sua senha antiga não está correta.")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password_confirm": "As senhas não coincidem."}
            )
        # Aqui daria pra incluir validação de força da senha
        return data
