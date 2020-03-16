######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.7.6-alpine

ENV HOME /home/$USER
WORKDIR $HOME

# Building numpy can get complicated
# https://www.freecodecamp.org/news/building-python-data-science-container-using-docker/
ENV PACKAGES="\
    dumb-init \
    musl \
    libc6-compat \
    linux-headers \
    build-base \
    bash \
    git \
    ca-certificates \
    freetype \
    libgfortran \
    libgcc \
    libstdc++ \
    openblas \
    tcl \
    tk \
"

# Install source code and required packages.
# Run dug to also install KGX.
RUN \
        apk add git && \
        apk add --no-cache --virtual build-dependencies $PACKAGES && \
        git clone https://github.com/helxplatform/dug.git && \
        cd dug && \
        pip install --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt && \
        bin/dug && \
        rm -rf /var/cache/apk/* && \
	apk del git

# Least privilege: Run as a non-root user.
ENV USER dug
ENV UID 1000
RUN adduser -D --home $HOME --shell /bin/bash --uid $UID $USER
RUN chown -R $UID:$UID $HOME

USER $USER

ENV PYTHONPATH $HOME/dug
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=
ENV COMMAND=crawl

WORKDIR $HOME/dug

# Define the generic search entrypoint providing elasticsearch connectivity information.
#ENTRYPOINT python search/search.py --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT $COMMAND
ENTRYPOINT bin/dug $COMMAND --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT
