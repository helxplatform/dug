######################################################
#
# A container for the core semantic-search capability.
#
######################################################
FROM python:3.13.14-alpine3.24


# Install required packages
RUN apk update && \
    apk add g++ make cargo rust git

RUN apk upgrade -Ua

RUN pip install --upgrade pip
# Create a non-root user.
ENV USER=dug
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

# Build caches are purged in the same layer as the install. Any dependency
# without a musllinux wheel gets compiled from its sdist here, which leaves the
# whole Cargo registry (~30MB of crate sources, each with its own Cargo.lock)
# and the pip cache behind -- Trivy reports every vulnerable crate in there as
# an image finding even though none of it ships in the running app.
RUN make install && \
    make install.dug && \
    rm -rf $HOME/.cargo $HOME/.cache $HOME/.rustup

# Drop pip now that everything is installed. dug never shells out to it at
# runtime, and pip pins its own vendored copies of msgpack and setuptools in
# pip/_vendor/vendor.txt -- scanners read those straight out of the base image,
# and only an upstream pip release can move them.
# ponytail: the rust/g++ toolchain stays. It scans clean, and apk del'ing it
# also drops libstdc++, which the compiled extensions link against.
USER root
RUN rm -rf /usr/local/lib/python3*/site-packages/pip \
           /usr/local/lib/python3*/site-packages/pip-*.dist-info \
           /usr/local/lib/python3*/ensurepip \
           $HOME/.local/lib/python3*/site-packages/pip \
           $HOME/.local/lib/python3*/site-packages/pip-*.dist-info \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.*
USER $USER

# Run it
ENTRYPOINT dug
