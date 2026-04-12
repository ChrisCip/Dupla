FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# Strip CRLF from checkout/editor on Windows; shebangs break if \r remains
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
