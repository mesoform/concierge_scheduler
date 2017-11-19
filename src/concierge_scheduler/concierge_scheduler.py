import os
import sys
import logging
import json
from pyzabbix import ZabbixAPI, ZabbixAPIException
from collections import defaultdict
import subprocess


__ENV_ZABBIX_API_HOST = 'ZBX_API_HOST'
__ENV_ZABBIX_USER = 'ZBX_USER'
__ENV_ZABBIX_PASS = 'ZBX_PASS'
__ENV_ZABBIX_CONFIG_DIR = 'ZBX_CONFIG_DIR'

action = sys.argv[1] if len(sys.argv) > 1 else 0
service_name = sys.argv[2] if len(sys.argv) > 2 else 0
current_scale = int(sys.argv[3]) if len(sys.argv) > 3 else 0
increment = int(sys.argv[4]) if len(sys.argv) > 4 else 0


__rules = {
        'applications': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'discoveryRules': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'graphs': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'groups': {
            'createMissing': 'true'
        },
        'hosts': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'images': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'items': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'maps': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'screens': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'templateLinkage': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'templates': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'templateScreens': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'triggers': {
            'createMissing': 'true',
            'updateExisting': 'true'
        },
        'valueMaps': {
            'createMissing': 'true',
            'updateExisting': 'true'
        }
    }


# logging

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    fmt = logging.Formatter('%(asctime)s [%(threadName)s] '
                            '[%(name)s] %(levelname)s: %(message)s')
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    return logger


__LOG = get_logger(__name__)


def __info(message, *args):
    __LOG.log(logging.INFO, message.format(*args))


def __log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


__zbx_api = None


# zabbix init

def initiate_zabbix_api(zbx_host, zbx_user, zbx_password):
    global __zbx_api
    zbx_url = 'http://{}'.format(zbx_host)
    __info('Logging in using url={} ...', zbx_url)
    __zbx_api = ZabbixAPI(zbx_url)
    __zbx_api.login(user=zbx_user, password=zbx_password)
    __info('Connected to Zabbix API Version {} as {}', __zbx_api.api_version(), zbx_user)


# scheduler

def pre_pem_file():
    create_pem_file("notes", 'key', service_name)
    create_pem_file("poc_1_notes", 'ca', service_name)
    create_pem_file("poc_2_notes", 'cert', service_name)


def create_pem_file(inv_property, filename, service_name):
    pem_file = __zbx_api.host.get(output=["host"], selectInventory=[inv_property], searchInventory={"alias": service_name})
    __info('Generating file {}.pem ...', filename)
    file = open('{}/{}.pem'.format(DOCKER_CERT_PATH, filename), 'w')
    file.write(pem_file[0]["inventory"][inv_property])


def scale_service(desired_scale):
    try:
        subprocess.call("/usr/local/bin/docker-compose --tlsverify --tlscert={}/cert.pem \
                  --tlscacert={}/ca.pem --tlskey={}/key.pem \
                  --host={} --file /tmp/docker-compose.yml --project-name dockerlx \
                  scale {}={}".format(DOCKER_CERT_PATH, DOCKER_CERT_PATH, DOCKER_CERT_PATH, DOCKER_HOST, service_name, desired_scale).split())
    except subprocess.CalledProcessError as err:
        __log_error_and_fail('docker-compose failed', err)
    else:
        __info("Scaled {} from {} to {}".format(service_name, current_scale, desired_scale))


def scale_up(current_scale, increment):
    pre_pem_file()
    desired_scale=(current_scale + increment)
    scale_service(desired_scale)


def scale_down(current_scale, increment):
    pre_pem_file()
    desired_scale=(current_scale - increment)
    scale_service(desired_scale)


def service_ps(*args):
    pre_pem_file()
    subprocess.call("/usr/local/bin/docker-compose --tlsverify --tlscert={}/cert.pem \
                      --tlscacert={}/ca.pem --tlskey={}/key.pem \
                      --host={} --file /tmp/docker-compose.yml --project-name dockerlx \
                      ps".format(DOCKER_CERT_PATH, DOCKER_CERT_PATH, DOCKER_CERT_PATH, DOCKER_HOST).split())


# backups aka exports

def __export_json_to_file(result, export_dir, export_filename):
    target_absolute_path = '{}/{}.json'.format(export_dir, export_filename)
    with open(target_absolute_path, "w") as export_file:
        export_file.write(result)


def __get_data(component, label_for_logging=None, **kwargs):
    if not label_for_logging:
        label_for_logging = '{}s'.format(component)
    __info('Exporting {}...', label_for_logging)
    # getattr is like concatenating component onto the object. In this case ZabbixAPI.template
    results = getattr(__zbx_api, component).get(**kwargs)
    if not results:
        __info('No {} found', label_for_logging)
        return
    print(results)
    return results


def __get_selected_data_and_export(component, get_event_source,
                                   export_dir, export_filename,
                                   label_for_logging=None):
    results = __get_data(component, label_for_logging,
                         output='extend',
                         selectOperations='extend',
                         selectRecoveryOperations='extend',
                         selectFilter='extend',
                         filter={'eventsource': get_event_source})

    __export_json_to_file(json.dumps(results), export_dir, export_filename)


def __get_data_and_export(component, get_output,
                          export_dir, export_filename, label_for_logging=None):
    results = __get_data(component, label_for_logging,
                         output=get_output)

    __export_json_to_file(json.dumps(results), export_dir, export_filename)


def __get_data_and_export_config(component, get_id_prop_name,
                                 export_option_name,
                                 export_dir, export_filename,
                                 label_for_logging=None):
    results = __get_data(component, label_for_logging,
                         output=get_id_prop_name)
    print(results)
    component_ids = [component[get_id_prop_name] for component in results]

    export_options = {export_option_name: component_ids}
    print(export_options)
    result = __zbx_api.configuration.export(options=export_options,
                                            format='json')

    __export_json_to_file(result, export_dir, export_filename)


def export_templates(export_dir):
    __get_data_and_export_config(
        'template', 'templateid', 'templates', export_dir, 'templates')


def export_host_groups(export_dir):
    __get_data_and_export_config(
        'hostgroup', 'groupid', 'groups', export_dir, 'hostgroups')


def export_hosts(export_dir):
    __get_data_and_export_config('host', 'hostid', 'hosts', export_dir, 'hosts')


def export_media_types(export_dir):
    __get_data_and_export('mediatype', 'extend', export_dir, 'mediatypes')


def export_auto_registration_actions(export_dir):
    __get_selected_data_and_export(
        'action', 2, export_dir, 'reg_actions', 'auto-registration actions')


def export_trigger_actions(export_dir):
    __get_selected_data_and_export(
        'action', 0, export_dir, 'trigger_actions', 'trigger actions')


def export_actions_data(export_dir):

    data = defaultdict(list)

    for template in __zbx_api.template.get(output="extend"):
        templates = {"templateid": template['templateid'], "host": template['host']}
        data['templates'].append(templates)

    for hostgroup in __zbx_api.hostgroup.get(output="extend"):
        hostgroups = {"groupid": hostgroup['groupid'], "name": hostgroup['name']}
        data['hostgroups'].append(hostgroups)

    target_path = '{}/actions_data_orig.json'.format(export_dir)
    with open(target_path, "w") as export_file:
         export_file.write(json.dumps(data))


def backup_app(export_dir):
    if not os.path.isdir(export_dir):
        os.makedirs(export_dir)

    for export_fn in [
                      export_templates,
                      export_host_groups,
                      export_hosts,
                      export_media_types,
                      export_auto_registration_actions,
                      export_trigger_actions,
                      export_actions_data
                     ]:
        export_fn(export_dir)


# imports

def __import_objects(component, import_dir):
    file = '{}/{}.json'.format(import_dir, component)
    with open(file, 'r') as f:
        component_data = f.read()
        __info('Importing {}...', component)
        try:
            __zbx_api.confimport('json', component_data, __rules)
        except ZabbixAPIException as err:
            print(err)


def __import_actions(component, import_dir):
    file = '{}/{}.json'.format(import_dir, component)
    with open(file, 'r') as f:
        component_data = f.read()
        __info('Importing {}...', component)
        actions = json.loads(component_data)
        for action in actions:
            __zbx_api.action.create(action)
            # try:
            #   __zbx_api.action.create(actions)
            # except ZabbixAPIException as err:
            #   print(err)


def import_hostgroups(import_dir):
    __import_objects('hostgroups', import_dir)


def import_templates(import_dir):
    __import_objects('templates', import_dir)


def import_hosts(import_dir):
    __import_objects('hosts', import_dir)


def import_actions(import_dir):
    __import_actions('reg_actions_import', import_dir)


def import_comp(import_dir, components):
    for import_fn in components:
        import_fn(import_dir)


def exp_act_data_dest(export_dir):
    data = defaultdict(list)

    for template in __zbx_api.template.get(output="extend"):
        templates = {"templateid": template['templateid'], "host": template['host']}
        data['templates'].append(templates)

    for hostgroup in __zbx_api.hostgroup.get(output="extend"):
        hostgroups = {"groupid": hostgroup['groupid'], "name": hostgroup['name']}
        data['hostgroups'].append(hostgroups)

    target_path = '{}/actions_data_dest.json'.format(export_dir)
    with open(target_path, "w") as export_file:
        export_file.write(json.dumps(data))


def get_all(act_line, key, orig, dest):
    if type(act_line) == str:
        act_line = json.loads(act_line)
    if type(act_line) is dict:
        for actjsonkey in act_line.copy():
            if type(act_line[actjsonkey]) in (list, dict):
                get_all(act_line[actjsonkey], key, orig, dest)
            elif actjsonkey == key:
                if key == 'templateid':
                    for tmplorig in orig["templates"]:
                        if tmplorig['templateid'] == act_line[actjsonkey]:
                            hostorig = tmplorig['host']
                            for tmpldest in dest["templates"]:
                                if hostorig == tmpldest['host']:
                                    act_line[actjsonkey] = tmpldest['templateid']
                elif key == 'groupid':
                    for grporig in orig["hostgroups"]:
                        if grporig['groupid'] == act_line[actjsonkey]:
                            hostorig = grporig['name']
                            for grpdest in dest["hostgroups"]:
                                if hostorig == grpdest['name']:
                                    act_line[actjsonkey] = grpdest['groupid']
                            break
            elif actjsonkey != key:
                if actjsonkey in ('actionid', 'maintenance_mode', 'eval_formula', 'operationid'):
                    del act_line[actjsonkey]
    elif type(act_line) is list:
        for item in act_line:
            if type(item) in (list, dict):
                get_all(item, key, orig, dest)


def gen_imp_act_file(files_dir):
    actions_file = '{}/reg_actions.json'.format(files_dir)
    actions_orig = '{}/actions_data_orig.json'.format(files_dir)
    actions_dest = '{}/actions_data_dest.json'.format(files_dir)

    actions_data = open(actions_file)
    data_orig = open(actions_orig)
    data_dest = open(actions_dest)
    data = json.load(actions_data)
    orig = json.load(data_orig)
    dest = json.load(data_dest)
    for act_line in data:
        get_all(act_line, 'groupid', orig, dest)
        get_all(act_line, 'templateid', orig, dest)

    target_path = '{}/reg_actions_import.json'.format(files_dir)
    with open(target_path, "w") as export_file:
        export_file.write(json.dumps(data))

    actions_data.close()


def import_app(import_dir):
    to_import = [import_hostgroups, import_templates, import_hosts]
    import_comp(import_dir, to_import)
    exp_act_data_dest(import_dir)
    gen_imp_act_file(import_dir)
    to_import = [import_actions]
    import_comp(import_dir, to_import)


# main

if __name__ == '__main__':
    from docker_env import *

    host = os.getenv(__ENV_ZABBIX_API_HOST)
    user = os.getenv(__ENV_ZABBIX_USER)
    password = os.getenv(__ENV_ZABBIX_PASS)
    config_dir = os.getenv(__ENV_ZABBIX_CONFIG_DIR) or \
                        os.path.abspath(__file__)

    initiate_zabbix_api(host, user, password)

    if action in ['scale_up', 'scale_down', 'service_ps']:
        fn = globals()[action]
        fn(current_scale, increment)
    elif action in ['backup_app', 'import_app']:
        fn = globals()[action]
        fn(config_dir)
    else:
        __log_error_and_fail('Unknown action {}', action)
