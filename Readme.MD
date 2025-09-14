# Sistema FIC

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

> O sistema tem como objetivo gerenciar incrições em cursos ofertados por uma instituição.

---

### 📚 Índice

* [Tecnologias Utilizadas](#-tecnologias-utilizadas)
* [Pré-requisitos](#-pré-requisitos)
* [🚀 Começando: Setup Inicial](#-começando-setup-inicial)
* [💻 Fluxo de Trabalho no Dia a Dia](#-fluxo-de-trabalho-no-dia-a-dia)
* [🛠️ Comandos Úteis](#️-comandos-úteis)

---

### ✨ Tecnologias Utilizadas

* **Backend:** Python, Django, Django Rest Framework
* **Banco de Dados:** PostgreSQL
* **Ambiente:** Docker, Docker Compose

---

### ✅ Pré-requisitos

Antes de começar, garanta que você tenha as seguintes ferramentas instaladas em sua máquina:
* **Visual Studio Code**
* **Docker** e **Docker Compose**

---

### 🚀 Começando: Setup Inicial

Siga estes passos **apenas na primeira vez** que for configurar o projeto. O objetivo é ter o ambiente completamente funcional em poucos minutos.

#### Passo 1: Clonar o Repositório
```bash
git clone git@github.com:kaellasales/SistemaFIC.git
cd sistemaFIC
```

#### Passo 2: Configurar Variáveis de Ambiente (`.env`)
As senhas e chaves do projeto são gerenciadas localmente e nunca devem ser enviadas para o Git.

a. Crie seu arquivo de ambiente local a partir do exemplo fornecido:
```bash
cp .env.example .env
```

b. **Abra o arquivo `.env`** e configure as variáveis. Preencha principalmente as seguintes:
```env
# Chave secreta do Django (pode gerar uma nova se quiser)
SECRET_KEY=sua_chave_secreta_aqui

# Configurações do Banco de Dados (pode manter o padrão para dev)
POSTGRES_DB=seu_db_dev
POSTGRES_USER=seu_user_dev
POSTGRES_PASSWORD=sua_senha_super_secreta

# Credenciais para o Superusuário que será criado automaticamente
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin
```

#### Passo 3: Construir e Iniciar o Ambiente Docker
Este é o comando principal. Ele vai construir a imagem da aplicação, baixar o Postgres e iniciar tudo de forma orquestrada.

```bash
docker-compose up --build
```

**O que acontece magicamente aqui?**
Ao executar este comando, o script `entrypoint.sh` dentro do contêiner será acionado **automaticamente** e fará o seguinte por você:
1.  Aguardará o banco de dados ficar pronto.
2.  Rodará o comando `python manage.py migrate`.
3.  Rodará o comando `python manage.py collectstatic`.
4.  Criará o superusuário com as credenciais do seu `.env`.
5.  Iniciará o servidor de desenvolvimento do Django.

Você verá os logs de todo esse processo no seu terminal.

#### Passo 4: Verificar a Instalação
Após o passo anterior ser concluído, abra seu navegador e acesse:

* **Aplicação:** [`http://localhost:8080/`](http://localhost:8080/)
* **Admin:** [`http://localhost:8080/admin/`](http://localhost:8080/admin/)

Use as credenciais `DJANGO_SUPERUSER_USERNAME` e `DJANGO_SUPERUSER_PASSWORD` do seu arquivo `.env` para logar no Admin.

**🎉 Parabéns, o ambiente está 100% configurado!**

---

### 💻 Fluxo de Trabalho no Dia a Dia

Depois da configuração inicial, sua rotina será muito mais simples.

* **Para iniciar o projeto:**
  ```bash
  docker-compose up
  ```
* **Para parar o projeto:**
  Pressione `Ctrl + C` no terminal e depois, para garantir que os contêineres sejam removidos, rode:
  ```bash
  docker-compose down
  ```

#### O Ciclo de Desenvolvimento (Quando Alterar `models.py`)
O comando `makemigrations` **NÃO** é automatizado, pois ele é uma ação que você, como desenvolvedor, deve tomar conscientemente.

1.  Altere um arquivo `api/models.py`.
2.  **Manualmente**, crie o novo arquivo de migração rodando:
    ```bash
    docker-compose exec -it fic bash
    ```
    ```bash
    python manage.py makemigrations
    ```

3.  **Commite o novo arquivo de migração** gerado na pasta `migrations/` para o Git.
4.  O `migrate` será aplicado automaticamente na próxima vez que você rodar `docker-compose up`.

---

### 🛠️ Comandos Úteis

Todos os comandos devem ser rodados na raiz do projeto.

* **Executar um comando `manage.py` qualquer:**
  Use o prefixo `docker-compose exec -it fic bash`.
  ```bash
  # Exemplo: Abrir o shell do Django
  docker-compose exec -it fic bash

  # Exemplo: rodar migrations(com o shell aberto, OK?)
  python manage.py makemigrations
  ```

* **Acessar o banco de dados diretamente (psql):**
  ```bash
  docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
  ```

* **Resetar completamente o banco de dados:**
  **CUIDADO:** Isso apagará todos os dados do seu banco de dados local.
  ```bash
  docker-compose down -v
  ```

* **Ver os logs da aplicação (se estiver rodando em background):**
  ```bash
  docker-compose logs -f web
  ```