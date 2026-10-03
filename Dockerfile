FROM python:3.14-slim AS python-deps

COPY requirements.txt /tmp/requirements.txt
# ponytail: nodriver 0.50.3 has a Latin-1 "±" in a comment (cdp/network.py), which Python 3.12+ refuses to
# import. Patch the byte (same one-liner as CI) and prove the import; drop both once a nodriver release fixes it.
RUN pip install --no-cache-dir --target /opt/python -r /tmp/requirements.txt \
    && PYTHONPATH=/opt/python python3 -c "import importlib.util as u, pathlib as p; f = p.Path(u.find_spec('nodriver').submodule_search_locations[0], 'cdp', 'network.py'); f.write_bytes(f.read_bytes().replace(b'\xb1Inf', b'+-Inf'))" \
    && PYTHONPATH=/opt/python python3 -c "import nodriver" \
    && find /opt/python -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /opt/python -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM python:3.14-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive

RUN printf 'Acquire::ForceIPv4 "true";\nAcquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/99fgc-net \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates tini \
        xvfb x11vnc novnc websockify \
    # Google Chrome where it exists (amd64): nodriver + Chrome claims Epic without a checkout captcha.
    # Google ships no Linux arm64 build, so ARM gets Debian's Chromium.
    && if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
           python3 -c "import urllib.request; urllib.request.urlretrieve('https://dl.google.com/linux/linux_signing_key.pub', '/etc/apt/keyrings/google-chrome.asc')" \
           && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.asc] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
           && apt-get update \
           && apt-get install -y --no-install-recommends google-chrome-stable; \
       else \
           apt-get install -y --no-install-recommends chromium; \
       fi \
    && printf '#!/bin/sh\nexit 0\n' > /usr/bin/xdg-open \
    && chmod +x /usr/bin/xdg-open \
    && mkdir -p /etc/opt/chrome/policies/managed /etc/chromium/policies/managed \
    && printf '%s\n' '{"AutoLaunchProtocolsFromOrigins":[{"protocol":"aliexpress","allowed_origins":["*"]},{"protocol":"aliexpresshd","allowed_origins":["*"]},{"protocol":"aecmd","allowed_origins":["*"]},{"protocol":"alibaba","allowed_origins":["*"]},{"protocol":"alipay","allowed_origins":["*"]},{"protocol":"alipays","allowed_origins":["*"]},{"protocol":"tmall","allowed_origins":["*"]},{"protocol":"taobao","allowed_origins":["*"]},{"protocol":"market","allowed_origins":["*"]},{"protocol":"intent","allowed_origins":["*"]}]}' \
       | tee /etc/opt/chrome/policies/managed/fgc-autolaunch.json /etc/chromium/policies/managed/fgc-autolaunch.json > /dev/null \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/* /var/tmp/* /tmp/* /usr/share/doc/* \
    && ln -sf /usr/share/novnc/vnc_auto.html /usr/share/novnc/index.html

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
ENV VNC_IDLE_TIMEOUT=60
EXPOSE 7080

ENV WIDTH=1280
ENV HEIGHT=720
ENV DEPTH=24
ENV SHOW=1

# Port check, not an HTTP GET: noVNC replaces the status server on this port while VNC is up.
HEALTHCHECK --interval=10s --timeout=5s CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 7080), timeout=3).close()"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python3", "main.py"]
