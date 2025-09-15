# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install git, Java 17, and Maven for cloning repositories and building Forge
RUN apt-get update && apt-get install -y git default-jdk maven && rm -rf /var/lib/apt/lists/*

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Clone the MTG-deck-testing repository into resources directory
RUN git clone https://github.com/ItsGoldeneyes/MTG-deck-testing.git /app/resources

# Clone the Forge repository
RUN git clone https://github.com/Card-Forge/forge.git /app/forge

# Build Forge using Maven
WORKDIR /app/forge
RUN mvn -U -B clean -P windows-linux install -DskipTests

# Copy forge-gui/res folder to forge-gui-desktop
RUN cp -r forge-gui/res forge-gui-desktop/target/

# Find the built JAR file and create a script to set the environment variable
RUN FORGE_JAR=$(find /app/forge -name "*forge-gui-desktop*jar-with-dependencies.jar" | head -1) && \
    echo "Found Forge JAR at: $FORGE_JAR" && \
    echo "#!/bin/bash" > /app/set_forge_path.sh && \
    echo "export FORGE_JAR_PATH='$FORGE_JAR'" >> /app/set_forge_path.sh && \
    echo "export FORGE_DECKS_PATH='/nonexistent/.forge/decks/constructed/JUMPSTART'" >> /app/set_forge_path.sh && \
    chmod +x /app/set_forge_path.sh

# Create Forge directory structure for appuser
RUN mkdir -p /nonexistent/.forge/decks/constructed/JUMPSTART && chown -R appuser:appuser /nonexistent/.forge

# Reset working directory
WORKDIR /app

# Create output directory structure and set proper permissions for appuser
RUN mkdir -p /app/output/logs /app/output/jumpstart && chown -R appuser:appuser /app/output

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 5000

# Run the application.
# CMD gunicorn 'worker:app' --bind=0.0.0.0:5000
CMD ["/bin/bash", "-c", "source /app/set_forge_path.sh && python worker.py"]
