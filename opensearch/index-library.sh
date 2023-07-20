#!/bin/sh

# DEV HOST
OPENSEARCH="https://localhost:9200"

# Apache Tika
TIKA="java -jar /Users/ft/Downloads/tika-app-2.8.0.jar -A"

# OUTPUT FILE
BULK="bulk.json"
rm $BULK

# indexMaterial( ID )
function indexMaterial {
    if [ -f $1/info.json ]; then
        echo "[+] indexing material with id $1"
        processMaterial $1
    else
        echo "[!] can't index material with id $1 because info.json is missing"
    fi

}

function parseTextContent {
    CONTENT=""

    CONTENT="$CONTENT $($TIKA $1 | tr '[:space:]' ' ' | tr -cd '[:alnum:] ://.,_')"

    echo $CONTENT
}

function processMaterial {
    echo "{ \"index\": { \"_index\": \"materials\", \"_id\": $1 } }" >> $BULK

    # Get thumbnails
    THUMBNAILS=""
    for img in $(ls $1/thumbnails/); do
        if [ -z "$THUMBNAILS" ]; then
            # First Thumbnail
            THUMBNAILS="\"$img\""
        else
            # Else
            THUMBNAILS="$THUMBNAILS, \"$img\""
        fi
    done

    # Get text content

    cat $1/info.json | \
    jq ".thumbnails = [$THUMBNAILS]" | \
    jq ".name_completion = $(jq ".name" $1/info.json)" | \
    jq ".text_content = \"$(parseTextContent $1/info.json)\"" | \
    jq -c \
    >> $BULK
}

echo "[i] Start indexing Education Matters Library"

MATERIAL_DIRS=$(ls -d [0-9]*)

for dir in $MATERIAL_DIRS; do
    indexMaterial $dir
done

curl -H "Content-Type: application/x-ndjson" -X PUT $OPENSEARCH/materials/_bulk -ku admin:admin --data-binary "@$BULK"

#rm $BULK