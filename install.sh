#!/bin/sh
rm /usr/bin/amigomake 2>/dev/null
ln -s $(pwd)/src/amigomake /usr/local/bin/amigomake
