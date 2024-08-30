FROM python:latest

COPY ./ /app/

RUN cd app && pip install -r requirements.txt

WORKDIR /app

RUN chmod +x /app/run_docker.sh
ENTRYPOINT "/app/run_docker.sh"
