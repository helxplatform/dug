######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:alpine3.20


# Install required packages
RUN apk update && \
    apk add g++ make libexpat=2.6.2-r0 libssl3=3.1.4-r6 libcrypto3=3.1.4-r6


#upgrade openssl \

#RUN apk  add openssl=3.1.4-r5


RUN pip install --upgrade pip
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
