#!/bin/bash

# Path: db_backup.sh

# This script will backup the Nautobot database and media files.
#
# If ENABLE_SCP_COPY is set to "True", the backup file will be copied to the remote server.
# Otherwise, the backup file will be kept in ${LOCAL_BACKUP_DATA_DIR} directory.
#
# Requirements:
#   Configure environment parameters in development/creds.env or .env
#
# Configuration:
#   LOCAL_BACKUP_DATA_DIR - (param: -d, --backup_directory) Directory where the backups are stored inside the subdirectory
#                           ${LOCAL_BACKUP_DATA_DIR}/${timestamp_string}/dump.sql
#                           ${LOCAL_BACKUP_DATA_DIR}/${timestamp_string}/media.tgz
#                           The backup files will be located in this directory.
#   BACKUP_FILENAME_STARTSWITH - (param -f, --filename-startswith) Filename of the backup file
#                           (e.g. nautobot-shut-no-shut will save the backup containing
#                           the dump.sql, media.tgz as nautobot-shut-no-shut.20230904-033002.tgz)
#   ENABLE_SCP_COPY       - (param: -s, --scp-enable)
#                           'True': backup file will be copied to the REMOTE_BACKUP_HOST
#                           'False': backup file will be kept in ${LOCAL_BACKUP_DATA_DIR}/${timestamp_string}/ directory
#   REMOTE_USERNAME       - (param: -u, --username) Username for scp
#   REMOTE_BACKUP_HOST    - (param: -h, --host) Host for scp - must be configured for passwordless connection (PublicKeyAuthentication)
#   REMOTE_BACKUP_DIR     - (param: -r, --remote-dir) Directory where the backups are stored (must be writeable for user ${REMOTE_USERNAME})
#
# Usage:
#   With environment variables:
#       ./db_backup_pgdb.sh
#   
#   with parameters:
#       ./db_backup_pgdb.sh -f nautobot-shut-no-shut -s True -d .backups -r /mnt/backup/backups/nautobot-shut-no-shut -h backupserver.example.local -u backup
#


SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}" )" &> /dev/null && pwd )"

# Activate the environment variables
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
BACKUP_FILENAME_STARTSWITH=${BACKUP_FILENAME_STARTSWITH:-"{{ cookiecutter.backup_filename_startswith }}/-app-/-"}
ENABLE_SCP_COPY=${ENABLE_SCP_COPY:-"True"}
LOCAL_BACKUP_DATA_DIR=${LOCAL_BACKUP_DATA_DIR:-"${SCRIPT_DIR}/.backups"}
REMOTE_BACKUP_DIR=${REMOTE_BACKUP_DIR:-"/mnt/backup/backups/{{ cookiecutter.backup_filename_startswith }}"}
REMOTE_BACKUP_HOST=${REMOTE_BACKUP_HOST:-"backupserver.example.local"}
REMOTE_USERNAME=${REMOTE_USERNAME:-"backup"}


# parse arguments to override default values
POSITIONAL=()
while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
    -f|--filename-startswith)
      BACKUP_FILENAME_STARTSWITH="$2"
      shift # past argument
      shift # past value
      ;;
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
      REMOTE_BACKUP_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    -h|--host)
      REMOTE_BACKUP_HOST="$2"
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


# Create timestamp string for backup files
timestamp_string=$(date "+%Y%m%d-%H%M%S")


# Create temporary directory and register cleanup function
tmp_dir=$( mktemp -d -t "${BACKUP_FILENAME_STARTSWITH}-XXXXXXXXXX" | tr -cd [:print:])
clean_up() {
  echo "Cleaning up temporary files in ${1}"
  rm -rf "${1}"
}
trap "clean_up $tmp_dir" EXIT


# Files in this directory will be deleted on exit.
backup_dir="${tmp_dir}/backup_files/${timestamp_string}"
backup_sql_filename="${backup_dir}/${BACKUP_FILENAME_STARTSWITH}.sql"
backup_media_filename="${backup_dir}/${BACKUP_FILENAME_STARTSWITH}.media.tgz"
temp_tar_name="${tmp_dir}/${BACKUP_FILENAME_STARTSWITH}.${timestamp_string}.tgz"

# set filename for local backup files
final_backup_name="${LOCAL_BACKUP_DATA_DIR}/${BACKUP_FILENAME_STARTSWITH}.${timestamp_string}.tgz"

# Create backup directory for this backup run and set permissions
mkdir -p "${backup_dir}"


# Backup Postgres Database
poetry run invoke backup-db --output-file="${backup_sql_filename}"
# Backup Nautobot media files (images, uploads)
poetry run invoke backup-media --output-file="${backup_media_filename}"
# Set permissions to allow access to the backup files at restore time
chmod -R 777 "${backup_dir}"


# List backup files in local backup directory
echo "Backup files:"
ls -la "${backup_dir}"


# tar all files in local backup directory
pushd "${tmp_dir}/backup_files" || exit
  # Allow completion of writing backup files
  sleep 2s
  tar -czf "${temp_tar_name}" "."
popd || exit


if [ "${ENABLE_SCP_COPY}" == "True" ]; then
  # Copy the file to final backup destination on remote server
  echo "Copy Backup to: ${REMOTE_USERNAME}@${REMOTE_BACKUP_HOST}:${REMOTE_BACKUP_DIR}"
  ssh "${REMOTE_USERNAME}@${REMOTE_BACKUP_HOST}" "bash -c 'mkdir -p ${REMOTE_BACKUP_DIR}'"
  scp "${temp_tar_name}" "${REMOTE_USERNAME}@${REMOTE_BACKUP_HOST}:${REMOTE_BACKUP_DIR}"
  final_backup_name="'${REMOTE_BACKUP_DIR}/${BACKUP_FILENAME_STARTSWITH}.${timestamp_string}.tgz' on server '${REMOTE_BACKUP_HOST}'"
else
  # Move the backup file to final backup destination
  mv "${temp_tar_name}" "${final_backup_name}"
fi

popd || exit
echo "" && \
echo "FINISHED BACKUP of Nautobot database and media-files!" && \
echo "Backup file: ${final_backup_name}" && \
echo "Backup content:" && \
tar -tvf "${temp_tar_name}" && \
echo "-----------------------------------------------------------------------" && \
echo ""
