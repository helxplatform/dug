######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM dhi.io/python:3.13-alpine3.22-dev AS builder

ARG USER=dug

# Install required packages
RUN apk update && \
    apk add g++ make cargo rust

RUN apk upgrade -Ua

RUN pip install --upgrade pip
# Create a non-root user.
ENV HOME=/home/$USER
ENV UID=1000

RUN adduser -D --home $HOME  --uid $UID $USER

USER $USER
WORKDIR $HOME

ENV PATH=$HOME/.local/bin:$PATH

# Copy over the source code
RUN mkdir dug
COPY --chown=$USER . dug/
WORKDIR $HOME/dug

RUN make install
RUN make install.dug

FROM dhi.io/python:3.13-alpine3.22
ARG USER
ENV HOME=/home/$USER

COPY --from=builder $HOME $HOME
USER $USER

# Run it
ENTRYPOINT dug
