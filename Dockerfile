ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    else \
      sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX} -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1 \
    STATE_DIR=/state \
    MEDIA_ROOTS=Mydata=/data/mydata

EXPOSE 8768
VOLUME ["/state"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8768", "--workers", "1"]
