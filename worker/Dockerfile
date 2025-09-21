# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install dependencies for Python, Java, GUI
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        maven \
        curl \
        unzip \
        ca-certificates \
        xvfb \
        fonts-dejavu \
        libasound2 \
        libasound2-plugins \
        pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Download and install Temurin OpenJDK 17
RUN curl -L https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.8_7.tar.gz \
    -o /tmp/openjdk17.tar.gz && \
    mkdir -p /opt/java && \
    tar -xzf /tmp/openjdk17.tar.gz -C /opt/java && \
    rm /tmp/openjdk17.tar.gz

ENV JAVA_HOME=/opt/java/jdk-17.0.8+7
ENV PATH="$JAVA_HOME/bin:$PATH"

# Download Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Clone and build Forge
RUN git clone https://github.com/Card-Forge/forge.git /app/forge
WORKDIR /app/forge
RUN mvn -U -B clean -P windows-linux install -DskipTests
RUN cp -r forge-gui/res forge-gui-desktop/target/
RUN cp -r forge-gui-desktop/target/* /app/

# Create Forge environment script
RUN FORGE_JAR=$(find /app/forge -name "*forge-gui-desktop*jar-with-dependencies.jar" | head -1) && \
    echo "#!/bin/bash" > /app/set_forge_path.sh && \
    echo "export FORGE_JAR_PATH='$FORGE_JAR'" >> /app/set_forge_path.sh && \
    echo "export FORGE_DECKS_PATH='/nonexistent/.forge/decks/constructed/JUMPSTART'" >> /app/set_forge_path.sh && \
    chmod +x /app/set_forge_path.sh

# Create necessary directories for Forge
RUN mkdir -p /nonexistent/.forge/decks/constructed/JUMPSTART && chown -R appuser:appuser /nonexistent/.forge
RUN mkdir -p /app/output/logs /app/output/jumpstart && chown -R appuser:appuser /app/output

WORKDIR /app
USER appuser

COPY . .

EXPOSE 5000

# Entrypoint script to auto-start Xvfb
RUN echo '#!/bin/sh\n\
mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix\n\
if ! pgrep Xvfb > /dev/null; then\n\
  Xvfb :99 -screen 0 1024x768x16 &\n\
fi\n\
export DISPLAY=:99\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command runs your Python worker
CMD ["bash", "-c", "source /app/set_forge_path.sh && python worker.py"]
