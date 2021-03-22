######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.8.5-slim

# Least privilege: Run as a non-root user.
ENV USER dug
ENV HOME /home/$USER
ENV UID 1000
RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER

# Install required packages
RUN apt-get update && \
    apt-get install -y curl gettext git gcc && \
    rm -rf /var/cache/apk/*


USER $USER
WORKDIR $HOME

ENV PATH=$PATH:$HOME/.local/bin

# Copy over the source code
RUN mkdir dug
COPY . dug/
WORKDIR $HOME/dug
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .

ENTRYPOINT dug