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


kubectl exec -it $pod -- bash -c "

    cd /erddapData

    mkdir -p storage/iot-data-landing/MockCo

    cd storage/iot-data-landing/MockCo

    dirs=("Sensor-1" "Sensor-1_QC" "Sensor-2" "Sensor-2_QC")

    for dir in \${dirs[@]}; do
        mkdir \$dir
    done

    exit
"

dirs=("Sensor-1" "Sensor-1_QC" "Sensor-2" "Sensor-2_QC")

for f in ${dirs[@]}; do
    echo "Running kubectl cp \"$(pwd)\"/dev/pvc/data/erddap/bootstraps/$f.jsonl $pod:/erddapData/storage/iot-data-landing/MockCo/$f/bootstrap.jsonl"
    kubectl cp "$(pwd)"/dev/pvc/data/erddap/bootstraps/$f.jsonl $pod:/erddapData/storage/iot-data-landing/MockCo/$f/bootstrap.jsonl
done
