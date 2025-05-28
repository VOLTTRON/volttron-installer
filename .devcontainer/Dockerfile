FROM python:3.10-slim

# Set shell to bash
SHELL ["/bin/bash", "-c"]

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages for VOLTTRON dependencies and development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    jq \
    sudo \
    vim \
    wget \
    unzip \
    libffi-dev \
    libssl-dev \
    procps \
    lsb-release \
    bash \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with sudo access
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Setup git for PR handling
RUN apt-get update && apt-get install -y \
    gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure git global settings
RUN git config --system pull.rebase false
RUN git config --system core.autocrlf input

# Add a script to help with PR testing
COPY ./test-pr.sh /usr/local/bin/test-pr
RUN chmod +x /usr/local/bin/test-pr

# Install Python development tools
RUN pip install --no-cache-dir \
    pytest \
    pylint \
    flake8 \
    black \
    mypy \
    pytest-cov

# Add user's local bin to PATH to avoid warnings about scripts not being on PATH
ENV PATH="/home/$USERNAME/.local/bin:$PATH"

# Create .bashrc if it doesn't exist and add PATH
RUN touch /home/$USERNAME/.bashrc && \
    echo 'export PATH=$PATH:/home/'$USERNAME'/.local/bin' >> /home/$USERNAME/.bashrc && \
    chown $USERNAME:$USERNAME /home/$USERNAME/.bashrc

# Create .ssh directory with correct permissions (will be mounted over)
RUN mkdir -p /home/$USERNAME/.ssh && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh && \
    chmod 700 /home/$USERNAME/.ssh

# Switch back to dialog for any ad-hoc use of apt
ENV DEBIAN_FRONTEND=dialog

# Set the default user
USER $USERNAME

# Add SSH to the known hosts
RUN mkdir -p ~/.ssh && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts