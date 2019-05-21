#!/bin/sh

set +x

make VERSION=`cat VERSION`
cp *.zip ../dist
