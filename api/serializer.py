from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from api.models import (
     Aluno, Estado, Municipio, Role, Professor
    )
User = get_user_model()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('name',)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance
        

class AlunoRegistroSerializer(UserSerializer):
    """
    Este serializer herda tudo do UserSerializer.
    A única coisa que ele faz a mais é adicionar a role "ALUNO" após a criação.
    """
    
    def create(self, validated_data):
        user = super().create(validated_data)
        aluno_role, _ = Role.objects.get_or_create(name="ALUNO")
        user.roles.add(aluno_role)
        return user

class AlunoPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aluno
        fields = (
            'data_nascimento', 'sexo', 'cpf',
            'numero_identidade', 'orgao_expedidor', 'uf_expedidor',
            'naturalidade', 'cep', 'logradouro', 'numero_endereco',
            'bairro', 'cidade', 'telefone_celular'
        )
    def create(self, validated_data):
        user = self.context['request'].user
        aluno, created = Aluno.objects.update_or_create(
            user=user,
            defaults=validated_data
        )
        return aluno

        return aluno
    

class ProfessorSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Professor
        fields = ['id','user', 'siape', 'cpf', 'data_nascimento']

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        professor = Professor.objects.create(user=user, **validated_data)
        professor_role, _ = Role.objects.get_or_create(name="PROFESSOR")
        user.roles.add(professor_role)
        return professor
        

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    class Meta:
        fields = ('email',)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True) # Renomeado para clareza
    new_password_confirm = serializers.CharField(write_only=True, required=True) # Adicionado para confirmação

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Sua senha antiga não está correta.")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "As senhas não coincidem."})
        # Você pode adicionar validação de força da senha aqui se quiser
        return data