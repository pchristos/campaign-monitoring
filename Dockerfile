FROM python:2.7-alpine

RUN apk add --update --no-cache \
    g++ \
    gcc

COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

COPY . /campaign

WORKDIR /campaign

EXPOSE 8000

ENTRYPOINT ["/campaign/bin/docker-init"]

CMD ["/campaign/bin/runserver"]
