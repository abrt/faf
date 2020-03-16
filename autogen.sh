#!/bin/sh

autoreconf --install --force
if [ -z "$NOCONFIGURE" ]; then
    ./configure "$@"
fi
