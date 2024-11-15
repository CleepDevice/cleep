#!/bin/bash

CLEEP_VERSION=$(cat cleep/__init__.py | grep version | awk '{ gsub(/"/,"",$3); print $3 }')
echo "CLEEP_VERSION=$CLEEP_VERSION"

# fix version in index.html to refresh cached files
grep -rl "?cleepversion" debian/cleep/opt/cleep/html | xargs sed -i 's/?cleepversion/?v'"$CLEEP_VERSION"'/g'

# minify binary from https://github.com/tdewolff/minify

# minify non minified js files
for FILE in $(find debian/cleep/opt/cleep/html/js/ -name '*.js' ! -name '*.min.js'); do
	FILENAME=$(basename $FILE)
    FILENAME_MIN=$(basename $FILE .js).min.js
    debian/minify -o $(dirname $FILE)/$FILENAME_MIN $FILE
    grep -rl "$FILENAME" debian/cleep/opt/cleep/html/index.html | xargs sed -i 's/'"$FILENAME"'/'"$FILENAME_MIN"'/g'
    rm $FILE
done

# minify css
debian/minify -o debian/cleep/opt/cleep/html/css/cleep.min.css debian/cleep/opt/cleep/html/css/cleep.css 

