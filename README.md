# Concierge Scheduler

This part of the Concierge Paradigm concerns how we coordinate the scaling of our services.

The Concierge acting in the role of concierge_scheduler.sh is taking a request from its client to manage their business schedule. As such when some particular resource gets low, order some more; and when something is no longer being used, get rid of it.

## Environment Variables

Set the following environment variables in the docker-compose yml file:

`ZBX_API_HOST`: The Zabbix web frontend endpoint \
`ZBX_USER`: A Zabbix username to access the web API \
`ZBX_PASS`: Password for the above Zabbix username \
`ZBX_CONFIG_DIR`: The source path for the Zabbix backup files 

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

1. **service_ps**: this action will run `docker-compose ps` and provide a list of what containers are currently running.

    It takes two arguments: `service_ps` + `<component>`
    
    Example: `concierge_scheduler service_ps consul`
    
    Logic insight:
    
    Given a component (e.g: consul), functions `pre_pem_file` and `generate_pem_file` construct certificates from the inventory of a component dummy host containing the relevant data and call function `service_ps` to provide the list of running containers. Once the result is provided the certificates will be deleted.
  
2. **backup_app**: this action will make an export of the below components existing in Zabbix.

    List of components: templates, hostgroups, hosts, mediatypes, auto-registration actions and triggers actions.
  
    It only takes one argument: `backup_app`
    
    Example: `concierge_scheduler backup_app`
    
    Logic insight:
    
    Different Zabbix API methods are used to export components.
    * Function `export_templates` exports all templates configuration data to file `templates.json` using the configuration.export method. 
    * Function `export_host_groups` exports all hostgroups configuration data to file `hostgroups.json` using the configuration.export method. 
    * Function `export_hosts` exports all hosts configuration data to file `hostgroups.json` using the configuration.export method. 
    * Function `export_media_types` exports all mediatypes configuration data to file `mediatypes.json` using the get method.
    * Function `export_auto_registration_actions` exports all auto-registration actions configuration data to file `reg_actions.json` using the get method.
    * Function `export_trigger_actions` exports all trigger actions configuration data to file `trigger_actions.json` using the get method.
    * Function `export_actions_data` export all templates and hostgroups names and ids to file `actions_data_orig.json` using get methods. This file can be later used to import auto-registration actions.
  
3. **import_app**: this action will make an import of the below components using a set of backup files as source from the      assigned configuration directory.

    List of components: hostgroups, templates, hosts, auto-registration actions, triggers actions, mediatypes.
  
    It only takes one argument: `import_app`
    
    Example: `concierge_scheduler import_app`
  
4. **scale_up**: this action will increment the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<increment>`
    
    Example: `concierge_scheduler scale_up consul 1 1`
  
5. **scale_down**: this action will decrease the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<decrement>`
  
    Example: `concierge_scheduler scale_down consul 2 1`
  
With container infrastructures, like Joyent's Triton, that manage placement of containers and allow containers to be first-class citizen's on the host and network, simply running docker-compose will be fine. However, when running containers on other infrastructures you may need to perform a little extra work to set up Docker Engine in Swarm Mode and scale services using docker service.

