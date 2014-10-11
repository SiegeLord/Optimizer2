#!/bin/sh
 
pandoc doc/guide.md -o guide.html -c doc/style.css --toc -B doc/header.html
