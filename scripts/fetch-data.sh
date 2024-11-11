#!/bin/bash

set -euo pipefail

mkdir -p dumps

cd dumps

wget -r -l1 -nd -A "taxdmp*.zip" -H -np -erobots=off https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/

for zipfile in *.zip; do
    dirname="$(basename "$zipfile" .zip)"
    mkdir -p "${dirname}"
    unzip -d "${dirname}" "${zipfile}"
    rm "${zipfile}"
done
