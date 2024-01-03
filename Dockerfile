######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.12.1-slim-bullseye

# Install required packages
RUN apt-get update && \
    apt-get install -y g++ make  && \
    rm -rf /var/cache/apt/*

# Create a non-root user.
ENV USER dug
ENV HOME /home/$USER
ENV UID 1000

RUN adduser --disabled-login --home $HOME --shell /bin/bash --uid $UID $USER

USER $USER
WORKDIR $HOME

ENV PATH=$HOME/.local/bin:$PATH

# Copy over the source code
RUN mkdir dug
COPY --chown=$USER . dug/
WORKDIR $HOME/dug

RUN make install
RUN make install.dug

# Run it
ENTRYPOINT dug