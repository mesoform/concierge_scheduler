# [Concierge Scheduler](http://www.mesoform.com/blog-listing/info/the-concierge-paradigm/)

This part of the [Concierge Paradigm](http://www.mesoform.com/blog-listing/info/the-concierge-paradigm) concerns how we coordinate the scaling of our services.

The Concierge acting in the role of concierge_scheduler.sh is taking a request from its client to manage their business schedule. As such when some particular resource gets low, order some more; and when something is no longer being used, get rid of it.


## Environment Variables

Set the following environment variables in the docker-compose.yml file for the Zabbix server service:

`ZBX_API_HOST`: The Zabbix web frontend endpoint \
`ZBX_API_USER`: A Zabbix username to access the web API \
`ZBX_API_PASS`: Password for the above Zabbix username, or absolute path to password file \
`ZBX_CONFIG_DIR`: The source path for the Zabbix backup/export files \
`ZBX_TLS_VERIFY`: `'true'` to enable ssl verification (default), `'false'` to disable \
`ZBX_FORCE_TEMPLATES`: Will delete all templates in destination zabbix server before importing configuration. 
Setting to anything other than `'false'` will enable this. Can also use the `--force-templates` flag   
`GCP_CREDENTIAL_FILE:` Credential file of GCP service account for cloud storage   
`STORAGE_LOCATION`: Remote storage location to store configuration files in. 
E.g. Cloud Storage bucket name or Azure Container   
`STORAGE_FOLDER`: Folder within bucket/container to upload files to



Example:
```
ZBX_API_HOST: "zbxweb.svc.eb49da3d-7240-6e94-8e93-b65f3954c652.us-east-1.triton.zone"
ZBX_USER: "Admin"
ZBX_PASS: "zabbix"
ZBX_CONFIG_DIR: "/usr/lib/zabbix/app_config"
```

Set the following environment variables in the docker_env.py file:

`DOCKER_CERT_PATH`: The path where the certificates will be generated \
`DOCKER_HOST`: The Docker service API endpoint \
`COMPOSE_HTTP_TIMEOUT`: The time a request to the Docker daemon is allowed to hang before Compose considers it failed 

Example:
```
DOCKER_CERT_PATH = "/tmp/certs"
DOCKER_HOST = "tcp://us-east-1.docker.joyent.com:2376"
DOCKER_CLIENT_TIMEOUT = 800
COMPOSE_HTTP_TIMEOUT = 800
```

## Actions

Actions known to the scheduler include the following:

1. **list**: this action will run `docker-compose ps` and provide a list of what containers are currently running.

    It takes two arguments: `list` + `<component>`
    
    Example: `concierge_scheduler list consul`
    
    Logic insight:
    
    Given a component (e.g: consul), functions `pre_pem_file` and `generate_pem_file` construct certificates from the inventory of a component dummy host containing the relevant data and call function `list` to provide the list of running containers. Once the result is provided the certificates will be deleted.
  
2. **backup_config**: this action will make an export of the below components existing in Zabbix.

    List of components: templates, hostgroups, hosts, mediatypes, auto-registration actions and triggers actions.
  
    It only takes one argument: `backup_config`
    
    Example: `concierge_scheduler backup_config`
    
    Logic insight:
    
    Different Zabbix API methods are used to export components.
    * Function `export_templates` exports all templates configuration data to file `templates.json` using the configuration.export method. 
    * Function `export_host_groups` exports all hostgroups configuration data to file `hostgroups.json` using the configuration.export method. 
    * Function `export_hosts` exports all hosts configuration data to file `hostgroups.json` using the configuration.export method. 
    * Function `export_media_types` exports all mediatypes configuration data to file `mediatypes.json` using the get method.
    * Function `export_auto_registration_actions` exports all auto-registration actions configuration data to file `reg_actions.json` using the get method.
    * Function `export_trigger_actions` exports all trigger actions configuration data to file `trigger_actions.json` using the get method.
    * Function `export_actions_data` export all templates and hostgroups names and IDs to file `actions_data_orig.json` using get methods. This file can later be used to import auto-registration actions.
  
3. **restore_config**: this action will make an import of the below components using a set of backup files as source from the      assigned configuration directory.

    List of components: hostgroups, templates, hosts, auto-registration actions, triggers actions, mediatypes.
  
    It only takes one argument: `restore_config`
    
    Example: `concierge_scheduler restore_config`
    
    It also takes the flag: `--force-templates` which will force all templates on destination server to be deleted before importing the template configuration

    Logic insight:
        
    Different Zabbix API methods are used to import components.
    * Function `import_hostgroups` imports all hostgroups configuration data from file `hostgroups.json` using the configuration.import method. 
    * Function `import_templates` imports all templates configuration data from file `templates.json` using the configuration.import method. 
    * Function `import_hosts` imports all hosts configuration data from file `hosts.json` using the configuration.import method. 
    * Function `import_reg_actions` imports all auto-registration actions configuration data from file `reg_actions_import.json` using the create method. As we don't know beforehand which IDs will have the `templates` and `hostgroups` created by the above imports and these are necessary to create the auto-registration actions we use the following approach: 
        * Generate the json file `actions_data_dest.json` with `hostgroups` and `templates` info from the destination Zabbix server (where the import is happening) using the `__exp_act_data_dest` function. We already have the json file `actions_data_orig.json` with `hostgroups` and `templates` info from the origin Zabbix server (where the backup/export was done).
        * Loop through the `reg_actions.json` backup file using function `__get_autoreg_action_dict` to replace the origin `hostgroup` and `template` IDs with the destination IDs using the above generated files and constructing the file `reg_actions_import.json` with the result. Some unnecessary keys are also removed while looping through the file.
        * Import the auto-registration actions making a request to the action.create method using the newly generated `reg_actions_import.json` file.
    * Function `import_trig_actions` imports all trigger actions configuration data from file `trigger_actions_import.json` using the create method. Some unnecessary keys are removed from the backup file `trigger_actions.json` using function `__get_trigger_action_dict` which generates the desired file `trigger_actions_import.json`.
    * Function `import_mediatypes` imports all mediatypes configuration data from file `mediatypes.json` using the configuration.import method.
    * Function `import_services` imports all services configuration data from file `services.json` using the create method.
    * Function `import_proxies` imports all proxy configuration data from file `proxies.json` using the create method.
  
4. **scale_up**: this action will increment the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<increment>`
    
    Example: `concierge_scheduler scale_up consul 1 1`

    Logic insight:
    
    Given a component (e.g: consul) which needs to be scaled up, functions `pre_pem_file` and `generate_pem_file` construct certificates from the inventory of a component dummy host containing the relevant data and call function `scale_up` with the current number of containers for the component (`current_scale`) and the number we want to add (`increment`). Once the component is incremented  to the desired scale the certificates will be deleted.

5. **scale_down**: this action will decrease the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<decrement>`
  
    Example: `concierge_scheduler scale_down consul 2 1`
    
    Logic insight:
    
    Given a component (e.g: consul) which needs to be scaled down, functions `pre_pem_file` and `generate_pem_file` construct certificates from the inventory of a component dummy host containing the relevant data and call function `scale_down` with the current number of containers for the component (`current_scale`) and the number we want to reduce (`decrement`). Once the component is decremented to the desired scale the certificates will be deleted.

6. **upload**: this action will upload files in specified config directory to a cloud storage location. Defaults to using GCP Cloud Storage. 
    
### Individual Use
The scheduler can be used outside the concierge paradigm to perform Zabbix configuration import/exports. 
This will require the `pyzabbix` library.  
Backing up existing zabbix configuration:
```bash
export ZBX_CONFIG_DIR=/zbx-config/
export ZBX_API_USER="Admin"
export ZBX_API_HOST="http://company-zabbix-frontend.com/"
export ZBX_API_PASS="zabbix"
export ZBX_TLS_VERIFY='false'

##Backup existing configuration
python concierge_scheduler.py event backup_config

##Restore configuration from configuration files
python concierge_scheduler.py event restore_config

##Upload ZBX_CONFIG_DIR to GCS bucket 
export GCP_CREDENTIAL_FILE=/credentials-file.json
export STORAGE_LOCATION=gcs-bucket-name
export STORAGE_FOLDER=subfolder-for-config-folders

python concierge_scheduler.py cloud upload
```


## Notes

* With container infrastructures, like Joyent's Triton, that manage placement of containers and allow containers to be first-class citizen's on the host and network, simply running docker-compose will be fine. However, when running containers on other infrastructures you may need to perform a little extra work to set up Docker Engine in Swarm Mode and scale services using docker service.
* If using scheduler for importing zabbix configuration, do not use in a server where existing configuration is needed.
  Importing configuration will remove the existing configuration.
