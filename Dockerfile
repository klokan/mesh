FROM alpine:3.7
ENV VIRTUAL_ENV=/usr/local
WORKDIR /usr/local/src/mesh

RUN apk -q --update --no-cache add  \
    gcc \
    linux-headers \
    musl-dev \
    python3 \
    python3-dev

COPY Pipfile Pipfile.lock /usr/local/src/mesh/

RUN python3 -m venv /usr/local \
&& pip -q install pipenv \
&& pipenv install
