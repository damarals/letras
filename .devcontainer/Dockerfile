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

# Essentials
RUN apt-get update \
    && apt-get install build-essential -y

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