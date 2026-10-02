#!/bin/bash
set -e

cd /home/container

# First run: clone if .git doesn't exist yet
if [ ! -d .git ] && [ "${USER_UPLOAD}" == "0" ]; then
    echo "No git repository detected — cloning ${GIT_ADDRESS}..."

    CLEAN_URL=$(echo "${GIT_ADDRESS}" | sed -e 's/https:\/\///')

    if [ -n "${BRANCH}" ]; then
        git clone -b "${BRANCH}" "https://${USERNAME}:${ACCESS_TOKEN}@${CLEAN_URL}" /tmp/repo_clone
    else
        git clone "https://${USERNAME}:${ACCESS_TOKEN}@${CLEAN_URL}" /tmp/repo_clone
    fi

    # Move cloned contents (including hidden files like .git) into the container dir
    shopt -s dotglob
    mv /tmp/repo_clone/* /home/container/ 2>/dev/null || true
    shopt -u dotglob
    rm -rf /tmp/repo_clone
fi

# Subsequent runs: pull latest if AUTO_UPDATE is on
if [ -d .git ] && [ "${AUTO_UPDATE}" == "1" ]; then
    echo "Auto-update enabled — pulling latest changes..."
    git pull
fi

# Install requirements
REQ_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
if [ -f "${REQ_FILE}" ]; then
    echo "Installing requirements from ${REQ_FILE}..."
    pip install -r "${REQ_FILE}"
fi

# Install any extra packages
if [ -n "${PY_PACKAGES}" ]; then
    echo "Installing additional packages: ${PY_PACKAGES}"
    pip install ${PY_PACKAGES}
fi

# Launch the app
echo "Starting ${PY_FILE}..."
exec python "${PY_FILE}"