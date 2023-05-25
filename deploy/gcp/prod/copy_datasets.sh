#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No pod specified"
    exit 1
fi

pod="$1"

for f in "$(pwd)"/dev/pvc/data/erddap/datasets.d/*; do
    filename=$(basename "$f")
    echo "Running kubectl cp $f $pod:/datasets.d/$filename"
    kubectl cp $f $pod:/datasets.d/$filename
done