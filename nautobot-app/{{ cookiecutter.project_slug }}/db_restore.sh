#!/bin/bash

# Path: db_restore.sh

# This script will restore the Nautobot database and media files.
#
# If ENABLE_SCP_COPY is set to "True", the backup file will be copied from the remote server.
# Otherwise, the backup file will be read from ${LOCAL_BACKUP_DATA_DIR} directory.
#
# Requirements:
#   Configure environment parameters in development/creds.env or .env
#
# Configuration:
#   LOCAL_BACKUP_DATA_DIR - (param: -d, --backup_directory) If ENABLE_SCP_COPY is set to "False", the backup file will be read from this directory.
#   ENABLE_SCP_COPY       - (param: -s, --scp-enable)
#                           'True': backup file will be copied from the REMOTE_BACKUP_HOST
#                           'False': backup file will be read from ${LOCAL_BACKUP_DATA_DIR} directory
#   REMOTE_USERNAME       - (param: -u, --username) Username for scp
#   REMOTE_BACKUP_HOST    - (param: -h, --host) Host for scp - must be configured for passwordless connection (PublicKeyAuthentication)
#   REMOTE_RESTORE_DIR    - (param: -r, --remote-dir) Directory where the backups are stored on the REMOTE_BACKUP_HOST
#
# Usage:
#   With environment variables:
#       ./db_restore.sh
#
#   with parameters:
#       ./db_restore.sh -s True -d .backups -r /mnt/backup/backups/nautobot-shut-no-shut -h backupserver.example.local -u backup
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
pushd $SCRIPT_DIR || exit


# Read environment variables
for envfn in development/dev.env development/development.env development/creds.env .env
do
  if [ -f "${envfn}" ]; then
    echo "Reading: ${envfn}"
    source "${envfn}"
  fi
done


# Set default values
ENABLE_SCP_COPY=${ENABLE_SCP_COPY:-"True"}
LOCAL_BACKUP_DATA_DIR=${LOCAL_BACKUP_DATA_DIR:-"${SCRIPT_DIR}/.backups"}
REMOTE_RESTORE_DIR=${REMOTE_RESTORE_DIR:-"/mnt/swarm_shared/service/nornir-backup/{{ cookiecutter.backup_filename_startswith }}"}
BACKUP_FILENAME_STARTSWITH=${BACKUP_FILENAME_STARTSWITH:-"nautobot-shut-no-shut"}
REMOTE_BACKUP_HOST=${REMOTE_BACKUP_HOST:-"backupserver.example.local"}
REMOTE_USERNAME=${REMOTE_USERNAME:-"backup"}


# parse arguments to override default values
POSITIONAL=()
while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
    -s|--scp-enable)
      ENABLE_SCP_COPY="$2"
      shift # past argument
      shift # past value
      ;;
    -d|--backup_directory)
      LOCAL_BACKUP_DATA_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    -r|--remote-dir)
      REMOTE_RESTORE_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    -h|--host)
      REMOTE_BACKUP_HOST="$2"
      shift # past argument
      shift # past value
      ;;
    -f|--filename)
      BACKUP_FILENAME_STARTSWITH="$2"
      shift # past argument
      shift # past value
      ;;
    -u|--username)
      REMOTE_USERNAME="$2"
      shift # past argument
      shift # past value
      ;;
    *)    # unknown option
      POSITIONAL+=("$1") # save it in an array for later
      shift # past argument
      ;;
  esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters


# Determine the latest backup file and copy it to LOCAL_BACKUP_DATA_DIR
if [ "${ENABLE_SCP_COPY}" == "True" ]; then
  latest_backup=$(ssh -t "${REMOTE_USERNAME}@${REMOTE_BACKUP_HOST}" "ls -tr ${REMOTE_RESTORE_DIR}/*.tgz | tail -n 1 | tr -cd [:print:]")
else
  # find latest backup file in ${REMOTE_RESTORE_DIR} (must be in this directory and must be a .tgz file)
  latest_backup=$(find "${REMOTE_RESTORE_DIR}" -maxdepth 1 -type f -name "*.tgz" | sort | tail -n 1 | tr -cd [:print:])
fi
echo "    Latest backup file:          '${latest_backup}'"

# Allow restore of backup files with different Sources (e.g. nautobot-porduction, nautobot-shut-no-shut)
# BACKUP_FILENAME_STARTSWITH=$(basename "${latest_backup}" | cut -d"." -f1 )
restore_subdir=$(basename "${latest_backup}" | cut -d"." -f2)
echo "    Restoring backup file:       '${latest_backup}'"
echo "    Subdir:                      '${restore_subdir}'"
echo "    Backup filename starts with: '${BACKUP_FILENAME_STARTSWITH}'"


# Create temporary directory and register cleanup function
tmp_dir=$( mktemp -d -t "${BACKUP_FILENAME_STARTSWITH}-XXXXXXXXXX" | tr -cd [:print:])
clean_up() {
  echo "Cleaning up temporary files in ${1}"
  sudo chmod -R 777 "${1}"
  sudo rm -rf "${1}"
}
trap "clean_up $tmp_dir" EXIT

echo "Created temporary directory: ${tmp_dir}"

# Move the backup file to temporary directory
if [ "${ENABLE_SCP_COPY}" == "True" ]; then
  scp "${REMOTE_USERNAME}@${REMOTE_BACKUP_HOST}":"${latest_backup}" "${tmp_dir}/"
else
  cp "${latest_backup}" "${tmp_dir}"
fi
sudo chown -R "${USER}":"${USER}" "${tmp_dir}"
# Extract backup (.sql and media data) to LOCAL_BACKUP_DATA_DIR
tar -xzf "${tmp_dir}/${BACKUP_FILENAME_STARTSWITH}.${restore_subdir}.tgz" -C "${tmp_dir}/"
tree "${tmp_dir}"

# Restore database data
poetry run invoke import-db --input-file="${tmp_dir}/backups/${restore_subdir}/${BACKUP_FILENAME_STARTSWITH}.sql"
# Restore media files
poetry run invoke import-media --input-file="${tmp_dir}/backups/${restore_subdir}/${BACKUP_FILENAME_STARTSWITH}.media.tgz"

popd || exit
echo "Finished restore - ${latest_backup}"
