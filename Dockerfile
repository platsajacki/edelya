FROM python:3.14-slim AS builder

WORKDIR /tmp/app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libmagic-dev \
	&& rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .

RUN python -m pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.14-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"

RUN apt-get update \
	&& apt-get install -y --no-install-recommends libmagic1 \
	&& rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY src/ .
