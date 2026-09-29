FROM debian:bookworm-slim AS python-deps

ARG DEBIAN_FRONTEND=noninteractive
COPY requirements.txt /tmp/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && pip install --no-cache-dir --break-system-packages --target /opt/python -r /tmp/requirements.txt \
    && find /opt/python -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /opt/python -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM debian:bookworm-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive

RUN printf 'Acquire::ForceIPv4 "true";\nAcquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/99fgc-net \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates tini python3 \
        xvfb x11vnc novnc websockify \
        chromium \
    && printf '#!/bin/sh\nexit 0\n' > /usr/bin/xdg-open \
    && chmod +x /usr/bin/xdg-open \
    && mkdir -p /etc/opt/chrome/policies/managed /etc/chromium/policies/managed \
    && printf '%s\n' '{"AutoLaunchProtocolsFromOrigins":[{"protocol":"aliexpress","allowed_origins":["*"]},{"protocol":"aliexpresshd","allowed_origins":["*"]},{"protocol":"aecmd","allowed_origins":["*"]},{"protocol":"alibaba","allowed_origins":["*"]},{"protocol":"alipay","allowed_origins":["*"]},{"protocol":"alipays","allowed_origins":["*"]},{"protocol":"tmall","allowed_origins":["*"]},{"protocol":"taobao","allowed_origins":["*"]},{"protocol":"market","allowed_origins":["*"]},{"protocol":"intent","allowed_origins":["*"]}]}' \
       | tee /etc/opt/chrome/policies/managed/fgc-autolaunch.json /etc/chromium/policies/managed/fgc-autolaunch.json > /dev/null \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/* /var/tmp/* /tmp/* /usr/share/doc/* \
    && ln -sf /usr/share/novnc/vnc_auto.html /usr/share/novnc/index.html \
    && ln -sf /usr/bin/python3 /usr/bin/python

COPY --from=python-deps /opt/python /opt/python
ENV PYTHONPATH=/opt/python

WORKDIR /fgc
COPY main.py .env.example status_index.html ./
COPY src ./src
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ARG COMMIT=""
ARG BRANCH=""
ARG NOW=""
ENV COMMIT=${COMMIT}
ENV BRANCH=${BRANCH}
ENV NOW=${NOW}

ENV VNC_PORT=5900
ENV NOVNC_PORT=7080
ENV VNC_MODE=auto
ENV VNC_IDLE_TIMEOUT=60
EXPOSE 7080

ENV WIDTH=1280
ENV HEIGHT=720
ENV DEPTH=24
ENV SHOW=1

HEALTHCHECK --interval=10s --timeout=5s CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7080/status.json', timeout=3).read()"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python3", "main.py"]
