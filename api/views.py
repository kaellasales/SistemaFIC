from rest_framework import generics, status, viewsets, permissions, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import Http404

from api.models import User, Estado, Municipio, Role, Aluno, Professor
from api.serializer import (
    AlunoRegistroSerializer, AlunoPerfilSerializer, ProfessorSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, ChangePasswordSerializer
)


class AlunoRegistroView(generics.CreateAPIView):
    """Endpoint público para que novos alunos possam se registrar."""
    serializer_class = AlunoRegistroSerializer
    permission_classes = [AllowAny]


class AlunoPerfilView(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      generics.GenericAPIView):
    """Endpoint único para gerenciar o perfil do aluno logado."""
    serializer_class = AlunoPerfilSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retorna o perfil do aluno vinculado ao usuário logado."""
        try:
            return Aluno.objects.get(user=self.request.user)
        except Aluno.DoesNotExist:
            raise Http404

    # --- Métodos HTTP ---

    def get(self, request, *args, **kwargs):
        """GET: Retorna o perfil do aluno logado."""
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """POST: Cria o perfil do aluno, se ainda não existir."""
        if Aluno.objects.filter(user=request.user).exists():
            raise ValidationError({"detail": "Perfil já existe. Para atualizar, use PUT ou PATCH."})
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """PUT: Atualiza o perfil do aluno por completo."""
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """PATCH: Atualiza o perfil do aluno parcialmente."""
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """DELETE: Remove o perfil do aluno."""
        return self.destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Associa o usuário logado ao criar o perfil."""
        serializer.save()


class ProfessorViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de professores."""
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer

    def get_permissions(self):
        """Define permissões diferentes para ações administrativas."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]


class PasswordResetRequestView(APIView):
    """Inicia o fluxo de 'esqueci minha senha' enviando um e-mail ao usuário."""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            # Gerar UID e Token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)

            # Montar link de reset
            reset_link = f"http://localhost:8080/reset-password/{uid}/{token}/"

            # Enviar e-mail
            send_mail(
                subject="Seu Link de Redefinição de Senha",
                message=f"Olá,\n\nClique no link para redefinir sua senha: {reset_link}\n\nObrigado.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )
        except User.DoesNotExist:
            # Não informar se o usuário existe ou não
            pass

        return Response(
            {"detail": "Se um usuário com este e-mail existir, um link de reset de senha foi enviado."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """Finaliza o fluxo de reset de senha validando o token e atualizando a senha."""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and PasswordResetTokenGenerator().check_token(user, token):
            user.set_password(password)
            user.save()
            return Response({"detail": "Senha redefinida com sucesso."}, status=status.HTTP_200_OK)

        return Response(
            {"detail": "O link de reset é inválido ou expirou."},
            status=status.HTTP_400_BAD_REQUEST
        )


class ChangePasswordView(generics.UpdateAPIView):
    """Permite que um usuário autenticado altere sua própria senha."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        """Valida e altera a senha do usuário logado."""
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Lida com o logout do usuário adicionando o refresh token à blacklist."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"detail": "Token inválido ou expirado"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
