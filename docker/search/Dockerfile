######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.7.6-alpine

WORKDIR /

# Install source code and required packages.
RUN apk add git && \
	git clone https://github.com/helxplatform/semantic-search.git && \
	cd semantic-search && \
	pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt && \
	apk del git

# Least privilege: Run as a non-root user.
ENV USER search-user
ENV UID 1000
ENV HOME /home/$USER
RUN adduser -D --home $HOME --shell /bin/bash --uid $UID $USER
RUN chown -R $UID:$UID $HOME

#RUN useradd -m -s /bin/bash -N -u $UID $USER
USER $USER
#WORKDIR $HOME

ENV PYTHONPATH /semantic-search
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=
ENV COMMAND=--crawl

WORKDIR /semantic-search/search

# Define the generic search entrypoint providing elasticsearch connectivity information.
ENTRYPOINT python search.py --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT $COMMAND
