# Official python:* images do not ship free-threaded builds yet (docker-library/python#1082).
# Base image for testing PEP 703 / Python 3.14t; revert to python:3.12-slim-bookworm for production.
# Builder stage
FROM tdciwasaki/python-nogil:3.14-slim-trixie AS builder

WORKDIR /app

# Slim base lacks build tools; pinned deps use wheels where available; uvicorn extras may still compile (e.g. httptools). pkg-config helps OpenSSL-backed builds if needed.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM tdciwasaki/python-nogil:3.14-slim-trixie

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

# Strip CRLF from checkout/editor on Windows; shebangs break if \r remains
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
