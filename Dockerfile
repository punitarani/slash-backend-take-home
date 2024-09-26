FROM python:3.12-slim

WORKDIR /app

# Install netcat for the waiting script and build tools
RUN apt-get update && apt-get install -y netcat-openbsd build-essential

# Install Python dependencies
COPY server/pyproject.toml server/poetry.lock /app/
RUN pip install poetry
RUN poetry config virtualenvs.create false && poetry install --no-dev

COPY server/ /app/

COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

EXPOSE ${PORT}

ENTRYPOINT ["/app/entrypoint.sh"]
