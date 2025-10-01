from rest_framework import generics, status, viewsets, permissions, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action

from api.permissions import IsProfessorUser, IsAlunoUser

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import Http404
from django.db import transaction

from api.models import (User, Estado, Municipio, Role, Aluno, Professor, Curso, InscricaoAluno)
from api.serializer import (
    AlunoRegistroSerializer, AlunoPerfilSerializer, ProfessorSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, 
    ChangePasswordSerializer, UserSerializer, UserUpdateSerializer,
    CursoSerializer, InscricaoAlunoSerializer
)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

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
            reset_link = f"http://localhost:8080/usuario/reset-password-confirm/{uid}/{token}/"

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



class UserViewSet(mixins.DestroyModelMixin, 
                  viewsets.GenericViewSet):
    """
    ViewSet minimalista que expõe APENAS as rotas de exclusão.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Define a permissão correta para a ação correta.
        - Ação 'me': Precisa estar autenticado.
        - Ação 'destroy': Precisa ser admin.
        """
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['delete'], url_path='me')
    def me(self, request, *args, **kwargs):
        """
        Endpoint para o usuário logado deletar a própria conta.
        URL: DELETE /api/users/me/
        """
        user = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class CursoViewSet(viewsets.ModelViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [IsProfessorUser] 

    def perform_create(self, serializer):
        """
        Este método é chamado pelo DRF antes de salvar um novo objeto.
        É o lugar perfeito para nossa regra de negócio!
        """
        # 1. Pega o perfil de professor do usuário logado.
        professor_criador = self.request.user.professor
        
        # 2. Salva o curso, passando o criador como argumento extra.
        # O DRF é inteligente e vai associar a FK 'criador' corretamente.
        curso_criado = serializer.save(criador=professor_criador)
        
        # 3. Adiciona o professor criador à lista ManyToMany de professores do curso.
        curso_criado.professores.add(professor_criador)


class InscricaoAlunoViewSet(mixins.CreateModelMixin, # Permite POST (create)
                            mixins.ListModelMixin,   # Permite GET (list)
                            mixins.RetrieveModelMixin, # Permite GET (retrieve by id)
                            viewsets.GenericViewSet):
    """
    ViewSet para gerenciar as inscrições de alunos.
    - Aluno: pode criar (solicitar) uma inscrição.
    - Admin: pode listar, ver e validar inscrições.
    """
    queryset = InscricaoAluno.objects.all()
    serializer_class = InscricaoAlunoSerializer

    def get_permissions(self):
        """Define permissões por ação."""
        if self.action == 'create':
            self.permission_classes = [IsAlunoUser]
        else: # list, retrieve, validar_inscricao
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Aluno solicita inscrição em um curso."""
        curso_id = request.data.get('curso_id')
        tipo_vaga_escolhido = request.data.get('tipo_vaga')
        aluno = request.user.aluno

        if not curso_id or not tipo_vaga_escolhido:
            return Response({'error': 'Os campos "curso_id" e "tipo_vaga" são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        if tipo_vaga_escolhido not in ['INTERNO', 'EXTERNO']:
            return Response({'error': 'O campo "tipo_vaga" deve ser "INTERNO" ou "EXTERNO".'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                curso = Curso.objects.select_for_update().get(id=curso_id)

                vagas_totais = curso.vagas_internas if tipo_vaga_escolhido == 'INTERNO' else curso.vagas_externas
                
                inscricoes_confirmadas = InscricaoAluno.objects.filter(
                    curso=curso, tipo_vaga=tipo_vaga_escolhido, status='CONFIRMADA'
                ).count()

                if inscricoes_confirmadas >= vagas_totais:
                    return Response({'error': 'Não há mais vagas disponíveis.'}, status=status.HTTP_400_BAD_REQUEST)

                inscricao, created = InscricaoAluno.objects.get_or_create(
                    aluno=aluno, curso_id=curso_id,
                    defaults={'status': 'AGUARDANDO_VALIDACAO', 'tipo_vaga': tipo_vaga_escolhido}
                )

                if not created:
                    return Response({'error': 'Você já solicitou inscrição neste curso.'}, status=status.HTTP_400_BAD_REQUEST)
                
                serializer = self.get_serializer(inscricao)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Curso.DoesNotExist:
            return Response({'error': 'Curso não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': 'Ocorreu um erro no servidor.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='validar')
    def validar_inscricao(self, request, pk=None):
        """Admin valida ou recusa uma inscrição pendente."""
        inscricao = self.get_object()

        if inscricao.status != 'AGUARDANDO_VALIDACAO':
            return Response({'error': 'Esta inscrição não está mais aguardando validação.'}, status=status.HTTP_400_BAD_REQUEST)

        aprovado = request.data.get('aprovar')
        if aprovado is None:
            return Response({'error': 'O campo "aprovar" (true/false) é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        inscricao.status = 'CONFIRMADA' if aprovado else 'CANCELADA'
        inscricao.save()
        
        # (Opcional) Enviar e-mail de notificação para o aluno aqui.
        
        serializer = self.get_serializer(inscricao)
        return Response(serializer.data, status=status.HTTP_200_OK)