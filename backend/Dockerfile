# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.14.6-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8

FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements.runtime.lock ./
RUN python -m pip wheel \
    --wheel-dir /wheels \
    --requirement requirements.runtime.lock

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel \
    --no-deps \
    --wheel-dir /wheels \
    .

FROM ${PYTHON_IMAGE} AS runtime

ARG DEBIAN_VERSION=12
ARG MSODBCSQL_VERSION=18.6.1.1-1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ARGOS_ENVIRONMENT=production \
    ARGOS_LOG_LEVEL=INFO

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl \
    && curl --fail --show-error --silent --location \
        --output /tmp/packages-microsoft-prod.deb \
        "https://packages.microsoft.com/config/debian/${DEBIAN_VERSION}/packages-microsoft-prod.deb" \
    && dpkg --install /tmp/packages-microsoft-prod.deb \
    && rm /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install --yes --no-install-recommends \
        libgssapi-krb5-2 \
        msodbcsql18=${MSODBCSQL_VERSION} \
        unixodbc \
    && apt-get purge --yes --auto-remove curl \
    && rm -rf /var/lib/apt/lists/* \
    && odbcinst -q -d | grep --fixed-strings --line-regexp \
        '[ODBC Driver 18 for SQL Server]'

COPY --from=builder /wheels /wheels
RUN python -m pip install \
        --no-index \
        --find-links=/wheels \
        argos-backend \
    && rm -rf /wheels \
    && groupadd --gid 10001 argos \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --no-create-home \
        --shell /usr/sbin/nologin \
        argos

WORKDIR /app
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["python", "-m", "uvicorn", "argos.main:app", "--host", "0.0.0.0", "--port", "8000"]
