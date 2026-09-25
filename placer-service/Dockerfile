# syntax=docker/dockerfile:1
FROM python:3.11.14-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gosu && rm -rf /var/lib/apt/lists/*
ARG FLYCTL_VERSION=0.4.108
RUN set -eux; \
    case "$(dpkg --print-architecture)" in amd64) arch=x86_64 ;; arm64) arch=arm64 ;; *) exit 1 ;; esac; \
    archive="flyctl_${FLYCTL_VERSION}_Linux_${arch}.tar.gz"; \
    base="https://github.com/superfly/flyctl/releases/download/v${FLYCTL_VERSION}"; \
    curl -fsSL "$base/$archive" -o "/tmp/$archive"; \
    curl -fsSL "$base/flyctl_${FLYCTL_VERSION}_checksums.txt" -o /tmp/fly-checksums; \
    cd /tmp; grep " $archive$" fly-checksums | sha256sum -c -; \
    tar -xzf "$archive" -C /usr/local/bin flyctl; \
    ln -s /usr/local/bin/flyctl /usr/local/bin/fly; \
    rm -f "$archive" fly-checksums

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY automation/ automation/
COPY utils/ utils/
COPY monitoring/ monitoring/
COPY prediction/ prediction/
COPY metrics/ metrics/
COPY config/ config/
COPY main.py ./
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app && mkdir -p data && chown -R app:app /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://localhost:8000/health || exit 1
ENTRYPOINT ["/entrypoint.sh"]
