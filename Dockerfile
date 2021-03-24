######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.8.5-slim

# Install required packages
RUN apt-get update && \
    apt-get install -y curl gettext git gcc make && \
    rm -rf /var/cache/apk/*

# Create a non-root user.
ENV USER dug
ENV HOME /home/$USER
ENV UID 1000

RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER

USER $USER
WORKDIR $HOME

ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=

# Copy over the source code
RUN mkdir dug
COPY --chown=$USER . dug/
WORKDIR $HOME/dug

# Set up the Python environment
# See https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
ENV VIRTUAL_ENV=$HOME/dug/.venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN make install

# Run it
ENTRYPOINT dug