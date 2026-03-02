# Carrion: Spine — slim production image
FROM python:3.12-slim

RUN adduser --disabled-password --gecos "" carrion

WORKDIR /app

# Install package and dependencies only
COPY pyproject.toml VERSION ./
COPY carrion_spine ./carrion_spine
RUN pip install --no-cache-dir --no-deps . \
    && pip install --no-cache-dir "discord.py>=2,<3"

# Non-root run
USER carrion
ENV PYTHONUNBUFFERED=1

# Config and data via bind mounts; token via env
ENTRYPOINT ["carrion-spine", "run"]
CMD ["--config", "/etc/carrion-spine/config.toml"]
