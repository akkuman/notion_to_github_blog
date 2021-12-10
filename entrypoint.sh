#!/bin/bash

set -e

# ref: https://docs.github.com/cn/actions/creating-actions/dockerfile-support-for-github-actions#workdir
cd $GITHUB_WORKSPACE && ls && python /main.py