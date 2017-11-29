# Concierge Scheduler

This part of the Concierge Paradigm concerns how we coordinate the scaling of our services.

The Concierge acting in the role of concierge_scheduler.sh is taking a request from its client to manage their business schedule. As such when some particular resource gets low, order some more; and when something is no longer being used, get rid of it.

Actions known to the scheduler include the following:

1. **service_ps**: this action will run `docker-compose ps` and provide a list of what containers are currently running.

    It takes two arguments: `service_ps` + `<component>`
    
    Example run: `concierge_scheduler service_ps consul`
  
2. **backup_app**: this action will make an export of the below components existing in Zabbix.

    List of components: templates, hostgroups, hosts, mediatypes, auto-registration actions and triggers actions.
  
    It only takes one argument: `backup_app`
    
    Example run: `concierge_scheduler backup_app`
  
3. **import_app**: this action will make an import of the below components using a set of backup files as source from the      assigned configuration directory.

    List of components: hostgroups, templates, hosts, auto-registration actions, triggers actions, mediatypes.
  
    It only takes one argument: `import_app`
    
    Example run: `concierge_scheduler import_app`
  
4. **scale_up**: this action will increment the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<increment>`
    
    Example run: `concierge_scheduler scale_up consul 1 1`
  
5. **scale_down**: this action will decrease the number of containers on a selected component.

    It takes four arguments: `scale_up` + `<component>` + `<current_scale>` + `<decrement>`
  
    Example run: `concierge_scheduler scale_down consul 2 1`
  
With container infrastructures, like Joyent's Triton, that manage placement of containers and allow containers to be first-class citizen's on the host and network, simply running docker-compose will be fine. However, when running containers on other infrastructures you may need to perform a little extra work to set up Docker Engine in Swarm Mode and scale services using docker service.

