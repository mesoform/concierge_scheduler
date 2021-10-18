#!/bin/bash

BACKUP=false
RESTORE=false
UPLOAD=false
DELETE=false
while getopts brud flag
do
    case "${flag}" in
        b) BACKUP=true;;
        r) RESTORE=true;;
        u) UPLOAD=true;;
        d) DELETE=true;;
    esac
done

DATE=$( date '+%Y%m%d%H%M' )
export ZBX_CONFIG_DIR=${ZBX_CONFIG_DIR:-"/zbx-configs/$DATE"}


if [ $BACKUP == true ]; then
  echo "$( date -u '+%F %T') INFO: Backing up Zabbix configuration to $ZBX_CONFIG_DIR"
  if python /concierge_scheduler/concierge_scheduler/concierge_scheduler.py event backup_config; then
    echo "$( date -u '+%F %T') INFO: Zabbix configuration backed up."
  else
    echo "$( date -u '+%F %T') ERROR: Failed to backup Zabbix configuration"
    exit 1
  fi
fi
if [ $RESTORE == true ]; then
  echo "$( date -u '+%F %T') INFO: Restoring Zabbix configuration from $ZBX_CONFIG_DIR"
  if python /concierge_scheduler/concierge_scheduler/concierge_scheduler.py event backup_config; then
    echo "$( date -u '+%F %T') INFO: Restored configuration to $ZBX_API_HOST"
  else
    echo "$( date -u '+%F %T') ERROR: Failed to restore zabbix configuration"
    exit 1
  fi
fi
if [ $UPLOAD == true ]; then
  echo "$( date -u '+%F %T') INFO: Uploading $ZBX_CONFIG_DIR to cloud"
  if python /concierge_scheduler/concierge_scheduler/concierge_scheduler.py cloud upload; then
    echo "$( date -u '+%F %T') INFO: Uploaded to cloud"
  else
    echo "$( date -u '+%F %T') ERROR: Failed to upload to cloud"
    exit 1
  fi
fi
if [ $DELETE == true ]; then
  echo "$( date -u '+%F %T') INFO: Deleting $ZBX_CONFIG_DIR"
  rm -r "$ZBX_CONFIG_DIR"
fi
