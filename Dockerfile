######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.8.5-slim

# Install required packages
RUN apt-get update && \
    apt-get install -y make && \
    rm -rf /var/cache/apk/*

# Create a non-root user.
ENV USER dug
ENV HOME /home/$USER
ENV UID 1000

RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER

USER $USER
WORKDIR $HOME

ENV PATH="$HOME/.local/bin:$PATH"
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=

# Copy over the source code
RUN mkdir dug
COPY --chown=$USER . dug/
WORKDIR $HOME/dug

RUN make install

# Run it
ENTRYPOINT dug