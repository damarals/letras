FROM python:3.11-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

ARG USERNAME=letras
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Configurar PATH
ENV PATH=/root/.local/bin:/home/$USERNAME/.local/bin:$PATH

# Instalar pipx
RUN python3 -m pip install pipx \
    && python3 -m pipx ensurepath --force

# Add PostgreSQL repository and install PostgreSQL 15 client
RUN apt-get update \
    && apt-get install -y curl gnupg2 lsb-release \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/postgresql.list \
    && apt-get update \
    && apt-get install -y build-essential postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/*

# Limpeza final
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Crie o usuário
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

USER $USERNAME

# Instalar Poetry
RUN pipx install poetry \
    && poetry config virtualenvs.in-project true \
    && poetry config virtualenvs.prompt "venv"

WORKDIR /home/letras/app

CMD ["tail", "-f", "/dev/null"]