#!/bin/sh

set +x

if [ -z "$BUCKET" ]; then
    echo "Missing input BUCKET"
    exit 1
fi

if [ -z "$PROJECT" ]; then
    echo "Missing input PROJECT"
    exit 1
fi

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "Missing input AWS_ACCESS_KEY_ID"
    exit 1
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Missing input AWS_SECRET_ACCESS_KEY"
    exit 1
fi

VERSION=`cat VERSION`
if [ -z "$VERSION" ]; then
    echo "Cannot find VERSION"
    exit 1
fi

URL="s3://$BUCKET/$PROJECT/$PROJECT-$VERSION.zip"
aws s3 ls "$URL" >/dev/null
if [ $? = 0 ]; then
    echo "$URL already exists! (Oops)"
    exit 1
fi
echo "$URL does not exist yet. (OK)"

    
