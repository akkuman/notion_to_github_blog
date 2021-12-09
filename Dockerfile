FROM python:3.7-slim-buster

LABEL maintainer="Akkuman<akkumans@qq.com> (https://hacktech.cn)"

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    # pip:
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

COPY ./requirements.txt ./
RUN pip3 install --no-cache-dir --no-compile -r requirements.txt

COPY ./entrypoint.sh ./main.py ./
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
