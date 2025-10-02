# Use Python 3.12 slim from your private registry
ARG REGISTRY_BASE=europe-west6-docker.pkg.dev/axach-inetbuildingzonereg-ibz/docker-hub-remote-repo/
FROM ${REGISTRY_BASE}python:3.12-slim AS runtime

ARG TOKEN

# Ensure logs appear immediately
ENV PYTHONUNBUFFERED True

# uv environment (for dependency management)
ENV UV_SYSTEM_PYTHON=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_NO_CACHE=1
ENV UV_INDEX=https://oauth2accesstoken:$TOKEN@europe-west6-python.pkg.dev/axach-inetbuildingzonereg-ibz/axach-genai-core-services-pyrepo/simple

# Set working directory
ENV APP_HOME /app
WORKDIR $APP_HOME

# Copy Cloud Run service folder (your app code, requirements.txt, pyproject.toml)
COPY . ./

# Upgrade system packages
RUN apt-get update && apt-get -y upgrade

# Install uv and sync dependencies
RUN pip install uv
RUN uv sync --no-dev

# Expose the Cloud Run port
EXPOSE 8080

# Environment variables to prevent uv from attempting network operations at runtime
ENV UV_OFFLINE=true
ENV UV_FROZEN=true
ENV UV_NO_SYNC=true

ENV PYTHONPATH=/app/src
# Health check endpoint is included in main.py
# Start the app directly with Uvicorn
CMD ["uv", "run", "uvicorn", "src.main:app", "--host=0.0.0.0", "--port=8080"]