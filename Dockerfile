######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.8.5-slim

# Install required packages
RUN apt-get update && \
    apt-get install -y curl make && \
    rm -rf /var/cache/apk/*

RUN adduser --disabled-login --home /home/dug --shell /bin/bash --uid 1000 dug

USER dug
WORKDIR /home/dug

ENV PATH=/home/dug/.local/bin:$PATH

# Copy over the source code
RUN mkdir dug
COPY --chown=dug . dug/
WORKDIR /home/dug/dug

RUN make install