######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.8.5-slim

# Least privilege: Run as a non-root user.
ENV USER dug
ENV HOME /home/$USER
WORKDIR $HOME
ENV UID 1000
RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER && \
    chown -R $UID:$UID $HOME

# Install required packages
RUN apt update && \
    apt-get install -y curl gettext git gcc && \
    mkdir dug

# Copy over the source code
COPY . dug/

# Run dug to also install KGX
# NOTE: We're checking out the specific commit for KGX so
#       dug can run properly
RUN cd dug && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf kgx && \
    git clone https://github.com/NCATS-Tangerine/kgx.git && \
    cd kgx && \
    python setup.py install && \
    cd .. && \
    find . -type f -exec chmod 664 {} \; && \
    find . -type f -iname *.py -exec chmod 775 {} \; && \
    find bin -type f -exec chmod 775 {} \; && \
    find . -type d -exec chmod 775 {} \; && \
    chown -R $UID:$UID $HOME && \
    rm -rf /var/cache/apk/*

USER $USER
ENV PYTHONPATH $HOME/dug
ENV ELASTIC_API_HOST=
ENV ELASTIC_API_PORT=
ENV COMMAND=crawl
WORKDIR $HOME/dug

# Define the generic search entrypoint providing elasticsearch connectivity information.
ENTRYPOINT bin/dug $COMMAND --elastic-host=$ELASTIC_API_HOST --elastic-port=$ELASTIC_API_PORT
