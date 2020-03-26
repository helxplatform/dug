######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.7.6-alpine

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

# Least privilege: Run as a non-root user.
ENV USER dug
ENV HOME /home/$USER
WORKDIR $HOME
ENV UID 1000
RUN adduser -D --home $HOME --shell /bin/bash --uid $UID $USER
RUN chown -R $UID:$UID $HOME

# Install source code and required packages.
# Run dug to also install KGX.
RUN \
        apk add curl git && \
        apk add --no-cache --virtual build-dependencies $PACKAGES && \
        git clone https://github.com/helxplatform/dug.git && \
        cd dug && \
        pip install --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt && \
        bin/dug dev init  && \
        find . -type f -exec chmod 664 {} \; && \
        find . -type f -iname *.py -exec chmod 775 {} \; && \
        find bin -type f -exec chmod 775 {} \; && \
        find . -type d -exec chmod 775 {} \; && \
        rm -rf /var/cache/apk/* && \
	apk del git

USER $USER

ENV PYTHONPATH $HOME/dug
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=
ENV COMMAND=crawl

WORKDIR $HOME/dug

# Define the generic search entrypoint providing elasticsearch connectivity information.
ENTRYPOINT bin/dug $COMMAND --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT
