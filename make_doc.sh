#!/bin/sh
 
pandoc doc/guide.md -o index.html -c style.css --toc -B doc/header.html
