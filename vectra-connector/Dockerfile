FROM python:latest

COPY ./ /app/

RUN cd app && pip install -r requirements.txt

WORKDIR /app

RUN chmod +x run_docker.sh
ENTRYPOINT "./run_docker.sh"