#!/bin/bash
cat paper_urls.csv | grep $1 | cut -d, -f2,3 | uniq | awk -F, -e '{print "\""$1"\": " "\""$2"\"," }'

