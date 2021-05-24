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

# Create a non-root user.
ENV USER helx
ENV HOME /home/$USER
ENV UID 1000

RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER

USER $USER
WORKDIR $HOME

ENV PATH=$HOME/.local/bin:$PATH

# Copy over the source code
RUN mkdir helx
COPY --chown=$USER . helx/
WORKDIR $HOME/helx

RUN make install