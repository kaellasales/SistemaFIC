from rest_framework import generics, status, viewsets, permissions, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action

from api.permissions import IsProfessorUser, IsAlunoUser, IsAdminUser, IsCCAUser

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import Http404
from django.db import transaction

from api.models import (User, Estado, Municipio, Aluno, Professor, Curso, InscricaoAluno)
from api.serializer import (
    AlunoRegistroSerializer, AlunoPerfilSerializer, ProfessorSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, 
    ChangePasswordSerializer, UserSerializer, UserUpdateSerializer,
    CursoSerializer, InscricaoAlunoSerializer,PasswordResetSerializer,
    MunicipioSerializer, EstadoSerializer
)

import logging

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = UserSerializer(user).data

        # Se o user tiver perfil de aluno, adiciona no response
        if hasattr(user, "aluno"):
            data["aluno"] = AlunoPerfilSerializer(user.aluno).data
        elif hasattr(user, "professor"):
            data["professor"] = ProfessorSerializer(user.professor).data
        
        return Response(data)
    
class EstadoView(APIView): 
    def get(self, request):
        try:
            estados=Estado.objects.all()
            serializer=EstadoSerializer(estados, many=True)
            return Response(serializer.data, status.HTTP_200_OK)
        except Exception as e:
            logging.info(f'erro:{e}')
            return Response(status=status.HTTP_404_NOT_FOUND)


class MunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para listar Municípios.
    Pode ser filtrado por estado_id e por um termo de busca (search).
    URL: /municipios/?estado_id=5&search=forta
    """
    serializer_class = MunicipioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Esta função é o coração do filtro. Ela lê os parâmetros da URL.
        """
        queryset = Municipio.objects.all()
        
        # 1. Filtra por Estado (se o parâmetro 'estado_id' for enviado)
        estado_id = self.request.query_params.get('estado_id', None)
        if estado_id is not None:
            queryset = queryset.filter(estado_id=estado_id)

        # 2. Filtra pelo termo de busca (se o parâmetro 'search' for enviado)
        search_term = self.request.query_params.get('search', None)
        if search_term:
            # '__icontains' faz a busca "contém" sem diferenciar maiúsculas/minúsculas
            queryset = queryset.filter(nome__icontains=search_term)
        
        # 3. Ordena e limita o número de resultados para não sobrecarregar
        return queryset.order_by('nome')[:20]

# class MunicipioView(APIView):
#     def get(self, request, estado_id):
#         try:
#             municipios = Municipio.objects.filter(estado=estado_id)
#             serializer = MunicipioSerializer(municipios, many=True)
#             return Response(serializer.data, status.HTTP_200_OK)
#         except Exception as e:
#             return Response(status=status.HTTP_404_NOT_FOUND)


class FormOptionsView(APIView):
    """
    Endpoint que fornece as opções (choices) para os formulários do frontend.
    URL: /api/form-options/aluno-perfil/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Pega as opções diretamente da classe do modelo Aluno
        sexo_options = [{'value': choice[0], 'label': choice[1]} for choice in Aluno.SexoChoices.choices]
        orgao_expedidor_options = [{'value': choice[0], 'label': choice[1]} for choice in Aluno.OrgaoExpedidor.choices]
        
        # Monta a resposta em um JSON organizado
        options_data = {
            'sexo': sexo_options,
            'orgao_expedidor': orgao_expedidor_options,
        }
        
        return Response(options_data)

class AlunoRegistroView(generics.CreateAPIView):
    """Endpoint público para que novos alunos possam se registrar."""
    serializer_class = AlunoRegistroSerializer
    permission_classes = [AllowAny]


class AlunoPerfilView(APIView):
    """
    Endpoint para gerenciar o perfil do aluno logado.
    - GET: Retorna o perfil se existir, 404 se não.
    - PATCH/PUT: Cria ou atualiza o perfil.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        GET: Apenas LÊ o perfil do aluno.
        """
        try:
            # Tenta buscar o perfil do aluno logado.
            profile = Aluno.objects.get(user=request.user)
            # Se encontrar, serializa e retorna os dados.
            serializer = AlunoPerfilSerializer(profile)
            return Response(serializer.data)
        except Aluno.DoesNotExist:
            # Se NÃO encontrar, retorna 404. É o sinal que o frontend espera
            # para saber que o formulário deve ficar em branco.
            return Response(status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, *args, **kwargs):
        """
        PATCH: Atualiza (ou cria, se não existir) o perfil do aluno.
        """
        try:
            # Tenta pegar a instância do perfil que já existe.
            instance = Aluno.objects.get(user=request.user)
            # Se encontrar, prepara o serializer para uma ATUALIZAÇÃO.
            serializer = AlunoPerfilSerializer(instance, data=request.data, partial=True)
        except Aluno.DoesNotExist:
            # Se não encontrar, prepara o serializer para uma CRIAÇÃO.
            serializer = AlunoPerfilSerializer(data=request.data, context={'request': request})

        # Valida os dados enviados...
        serializer.is_valid(raise_exception=True)
        # ...e salva (o .save() vai chamar 'update' ou 'create' do serializer, dependendo do caso).
        serializer.save(user=request.user)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # Fazemos o PUT se comportar exatamente como o PATCH
    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)



class ProfessorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para o CCA gerenciar Professores.
    Agora usa um único serializer principal para todas as ações.
    """
    queryset = Professor.objects.select_related('user').all()
    
    # Define o serializer padrão para o ViewSet
    serializer_class = ProfessorSerializer

    def get_permissions(self):
        """Sua lógica de permissões continua perfeita."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'set_password', 'list']:
            return [IsCCAUser()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        """
        Usa o serializer padrão, exceto para a ação 'set_password'.
        """
        if self.action == 'set_password':
            return PasswordResetSerializer
        return self.serializer_class # Usa o ProfessorSerializer para todo o resto

    # Sua ação 'set_password' já estava ótima e não precisa de mudanças.
    @action(detail=True, methods=['post'], permission_classes=[IsCCAUser])
    def set_password(self, request, pk=None):
        professor = self.get_object()
        user = professor.user
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_password = serializer.validated_data['new_password']
        
        user.set_password(new_password)
        user.save()
        
        return Response({'status': 'senha redefinida com sucesso'}, status=status.HTTP_200_OK)

    
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


class ChangePasswordView(APIView):
    """
    Endpoint para um usuário autenticado alterar sua própria senha.
    Usa um serializer customizado para validar e salvar a nova senha.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        # Passamos o 'context' para o serializer para que ele tenha acesso ao 'request'
        serializer = self.get_serializer(data=request.data)
        
        # Força a validação. Se falhar, levanta um erro 400.
        serializer.is_valid(raise_exception=True)
        
        # Se a validação passou, chamamos nosso método .save() customizado
        serializer.save()
        
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
    """
    ViewSet para Cursos, com status automático e permissões por perfil.
    """
    serializer_class = CursoSerializer
    
    def get_queryset(self):
        """
        Este método é o coração da lógica de visualização.
        Ele filtra quais cursos cada tipo de usuário pode ver.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Curso.objects.none()

        if user.groups.filter(name='PROFESSOR').exists():
            return Curso.objects.filter(criador=user.professor)
        
        if user.groups.filter(name='CCA').exists():
            return Curso.objects.all()
        
        # Alunos (ou qualquer outro grupo) só veem cursos com inscrições abertas.
        return Curso.objects.filter(status=Curso.StatusChoices.INSCRICOES_ABERTAS)

    def get_permissions(self):
        """
        Define quem pode fazer cada tipo de ação.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsProfessorUser]
        

        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        
        else:
            permission_classes = [permissions.IsAdminUser]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        Ao criar um curso ('POST'), o sistema define o professor logado como o 'criador'.
        O status será 'AGENDADO' por padrão, conforme definido no modelo.
        """
        # A permissão 'IsProfessorUser' já garante que request.user.professor existe.
        serializer.save(criador=self.request.user.professor)



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