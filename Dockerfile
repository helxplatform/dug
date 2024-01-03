######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.12.0-alpine3.18

# Install required packages
RUN apk update && \
    apk add g++ make    

# Create a non-root user.
ENV USER dug
ENV HOME /home/$USER
ENV UID 1000

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

# Run it
ENTRYPOINT dug