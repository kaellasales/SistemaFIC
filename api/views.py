from rest_framework import generics, status, viewsets, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from django.conf import settings
from django.core.mail import send_mail 
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import Http404

from api.models import (
    User, Estado, Municipio, Role, Aluno, Professor
    )

from api.serializer import (
   AlunoRegistroSerializer, AlunoPerfilSerializer, ProfessorSerializer, 
   PasswordResetRequestSerializer, PasswordResetConfirmSerializer, ChangePasswordSerializer
    )


class AlunoRegistroView(generics.CreateAPIView):
    """
    Endpoint público para que novos alunos possam se registrar.
    """
    serializer_class = AlunoRegistroSerializer
    permission_classes = [AllowAny] 


class AlunoPerfilView(generics.GenericAPIView):
    """
    View para gerenciar o perfil do aluno logado.
    - POST: Cria ou atualiza o perfil completo.
    - GET: Retorna o perfil existente.
    - PUT/PATCH: Atualiza o perfil existente.
    - DELETE: Remove o perfil.
    """
    serializer_class = AlunoPerfilSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Busca o perfil do aluno. Se não existir, levanta 404.
        Isso é o comportamento correto para GET, PUT, PATCH, DELETE.
        """
        try:
            return Aluno.objects.get(user=self.request.user)
        except Aluno.DoesNotExist:
            raise Http404

    # Método para CRIAR ou ATUALIZAR via POST
    def post(self, request, *args, **kwargs):
        # Passamos o 'request' no contexto para que o serializer tenha acesso ao 'user'
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        # O método .create() do nosso serializer fará a mágica do update_or_create
        aluno = serializer.save() 
        # Retornamos os dados atualizados com status 200 OK (ou 201 Created se preferir)
        return Response(self.get_serializer(aluno).data, status=status.HTTP_200_OK)

    # Método para LER o perfil
    def get(self, request, *args, **kwargs):
        aluno = self.get_object()
        serializer = self.get_serializer(aluno)
        return Response(serializer.data)

    # Método para ATUALIZAR o perfil
    def put(self, request, *args, **kwargs):
        aluno = self.get_object()
        serializer = self.get_serializer(aluno, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        aluno = self.get_object()
        serializer = self.get_serializer(aluno, data=request.data, partial=True) 
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    # Método para DELETAR o perfil
    def delete(self, request, *args, **kwargs):
        aluno = self.get_object()
        aluno.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProfessorViewSet(viewsets.ModelViewSet):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()] 
        return [IsAuthenticated()]
    

class PasswordResetRequestView(APIView):
    """Inicia o fluxo de "esqueci minha senha" enviando um e-mail para o usuário."""
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

            # Montar a URL
            reset_link = f"http://localhost:8080/reset-password/{uid}/{token}/"

            # Enviar o e-mail
            send_mail(
                subject="Seu Link de Redefinição de Senha",
                message=f"Olá,\n\nClique no link para redefinir sua senha:{reset_link}\n\nObrigado.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email]
            )
        except User.DoesNotExist:
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
            user.set_password(password) # set_password faz o hash correto
            user.save()
            return Response({"detail": "Senha redefinida com sucesso."}, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "O link de reset é inválido ou expirou."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class ChangePasswordView(generics.UpdateAPIView): # Pode usar uma view genérica
    """Permite que um usuário autenticado altere sua própria senha."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # O set_password agora pode ser feito aqui, com os dados validados
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """Lida com o logout do usuário adicionando o refresh token a uma blacklist."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"detail": "Token is invalid or expired"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)