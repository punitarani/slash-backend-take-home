#!/usr/bin/env bash

# Wait for RabbitMQ to be available
RABBITMQ_HOST=${RABBITMQ_HOST:-rabbitmq}
RABBITMQ_PORT=${RABBITMQ_PORT:-5672}

echo "Waiting for RabbitMQ at $RABBITMQ_HOST:$RABBITMQ_PORT..."
while ! nc -z $RABBITMQ_HOST $RABBITMQ_PORT; do
  echo "RabbitMQ not yet available..."
  sleep 2
done
echo "RabbitMQ is up!"

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-3000}"
