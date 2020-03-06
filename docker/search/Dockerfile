FROM python:3.7.6-alpine

WORKDIR /

# build-base linux-headers zeromq zeromq-dev && \

RUN apk add git && \
	git clone https://github.com/helxplatform/semantic-search.git && \
	cd semantic-search && \
	pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt && \
	apk del git

# build-base linux-headers zeromq-dev

ENV PYTHONPATH /semantic-search
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=
ENV PORT=5009

#ENTRYPOINT /usr/local/bin/gunicorn --workers=$WORKERS --bind=0.0.0.0:$PORT --name=$APP_NAME --timeout=600 --log-level=debug $APP_MODULE

ENTRYPOINT python /semantic-search/search/search.py --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT --crawl
