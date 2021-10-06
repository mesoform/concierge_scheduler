#!/usr/bin/env python
"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from pyzabbix import ZabbixAPIException
import json
import os
import sys
from collections import defaultdict
import logging
import hashlib

_ORIGINAL_IDS_FILE = 'id_map_backup.json'
_TRIGGER_ACTIONS_FILE = 'trigger_actions.json'
_REG_ACTIONS_FILE = 'reg_actions.json'
_rules = {
    'applications': {
        'createMissing': True,
        'deleteMissing': False
    },
    'discoveryRules': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': True
    },
    'graphs': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': False
    },
    'groups': {
        'createMissing': True
    },
    'hosts': {
        'createMissing': True,
        'updateExisting': True
    },
    'httptests': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': False
    },
    'images': {
        'createMissing': True,
        'updateExisting': True
    },
    'items': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': True
    },
    'maps': {
        'createMissing': True,
        'updateExisting': True
    },
    'mediaTypes': {
        'createMissing': True,
        'updateExisting': True,
    },
    'screens': {
        'createMissing': True,
        'updateExisting': True
    },
    'templateLinkage': {
        'createMissing': True,
        'deleteMissing': True
    },
    'templates': {
        'createMissing': True,
        'updateExisting': True
    },
    'templateScreens': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': True
    },
    'triggers': {
        'createMissing': True,
        'updateExisting': True,
        'deleteMissing': True
    },
    'valueMaps': {
        'createMissing': True,
        'updateExisting': True
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


def _info(message, *args):
    __LOG.log(logging.INFO, message.format(*args))


def _warn(message, *args):
    __LOG.log(logging.WARN, message.format(*args))


def _log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


class ZabbixAdmin:
    """
    Class for administering common operational activities for a Zabbix instance
    """

    def __init__(self, zbx_client, data_dir, force_template):
        """
        :param zbx_client: instance of a Zabbix API client object
        :param data_dir: directory where we will keep configuration data
        """
        self.zbx_client = zbx_client
        self.force_template = force_template
        self.imported_template_ids = []
        self.imported_hostgroup_ids = []
        self.imported_mediatype_ids = []
        self.imported_host_ids = []
        self.original_ids = {}
        self.dest_ids = defaultdict(dict)
        self.data_dir = data_dir
        self.original_ids_file = '{}/{}'.format(self.data_dir,
                                                _ORIGINAL_IDS_FILE)
        self.command_mapping = {
            'backup_config': self.backup_config,
            'restore_config': self.restore_config,
            'get_simple_id_map': self.get_id_file
        }
        self.id_mapping = {
            'templates': {'api_name': "template", 'id': "templateid", 'name': "host"},
            'mediatypes': {'api_name': "mediatype", 'id': "mediatypeid", 'name': "name"},
            'hostgroups': {'api_name': "hostgroup", 'id': "groupid", 'name': "name"},
            'hosts': {'api_name': "host", 'id': "hostid", 'name': "host"},
            'services': {'api_name': "service", 'id': "serviceid", 'name': "name"},
            'proxies': {'api_name': "proxy", 'id': "proxyid", 'name': "host"}
        }
        self.keys_to_remove = {
            'proxies': {'proxyid', 'lastaccess', 'auto_compress'},
            'trigger_actions': {'actionid', 'maintenance_mode', 'eval_formula', 'operationid'},
            'reg_actions': {'pause_suppressed', 'esc_period'}
        }

    def run(self, action):
        self.command_mapping[action]()

    # backups aka exports
    def _export_json_to_file(self, result, export_filename):
        target_absolute_path = '{}/{}.json'.format(self.data_dir,
                                                   export_filename)
        with open(target_absolute_path, "w") as export_file:
            export_file.write(result)

    def _get_data(self, component, label_for_logging=None, **kwargs):
        if not label_for_logging:
            label_for_logging = '{}s'.format(component)
        _info('Exporting {}...', label_for_logging)
        results = getattr(self.zbx_client, component).get(**kwargs)
        if not results:
            _info('No {} found', label_for_logging)
            return
        print(results)
        return results

    def export_action_config(self, event_source_id,
                             export_filename,
                             label_for_logging=None):
        """
        create a JSON file backup of the Zabbix actions configuration

        :param event_source_id: the ID of the type of action we want to export.
            E.g. 0 = trigger actions, 1 = discovery actions,
             2 = auto-registration actions, 3 = internal actions
        :param export_filename: the name to use for the output file
        :param label_for_logging: label we'll use when logging
        :return: file
        """
        results = self._get_data('action', label_for_logging,
                                 output='extend',
                                 selectOperations='extend',
                                 selectRecoveryOperations='extend',
                                 selectFilter='extend',
                                 filter={'eventsource': event_source_id})

        self._export_json_to_file(json.dumps(results), export_filename)

    def export_component(self, component,
                         export_filename,
                         label_for_logging=None):
        """
        create a JSON file backup of the Zabbix component configuration

        :param component: what media we want to export. E.g. mediatypes
        :param export_filename: the name to use for the output file
        :param label_for_logging: label we'll use when logging
        :return: file
        """
        results = self._get_data(component, label_for_logging,
                                 output='extend')

        self._export_json_to_file(json.dumps(results), export_filename)

    def export_component_config(self, component, id_prop_name,
                                export_option_name,
                                export_filename,
                                label_for_logging=None):
        """
        create a JSON file backup of Zabbix components like templates or hosts

        :param component: which component to export. E.g. hosts, hostgroups,
                        templates
        :param id_prop_name: the property name ehere our component IDs are
                        found. E.g. hostgroups = groupid
        :param export_option_name: there isn't a like-for-like map of the export
                option name and component name. E.g. templates = templates, but
                hostgroups = groups. Also, it is possible to specify a list of
                particular components to export. E.g. "hosts" ["10452", "12451"]
        :param export_filename: the name to use for the output file
        :param label_for_logging: label we'll use when logging
        :return: file
        """
        results = self._get_data(component, label_for_logging,
                                 output=id_prop_name)
        component_ids = [component[id_prop_name] for component in results]

        export_options = {export_option_name: component_ids}
        result = self.zbx_client.configuration.export(options=export_options,
                                                      format='json')

        self._export_json_to_file(result, export_filename)

    def get_id_file(self):
        """
        we need to have a simplified map of component IDs to their names because
        when we're importing things like auto-registration actions, we need to
        know what our old and new IDs are so we can correctly link them upon
        import.
        The hash of the components data (excluding id) is also stored for comparing data.

        :return: file
        """
        data = defaultdict(list)
        for component in ['templates', 'hostgroups', 'hosts', 'mediatypes']:
            component_id = self.id_mapping[component]['id']
            component_name = self.id_mapping[component]['name']
            for item in getattr(self.zbx_client, self.id_mapping[component]['api_name']).get(output="extend"):
                item_copy = dict(item)
                del item_copy[component_id]
                item_hash = hashlib.md5(json.dumps(item_copy, sort_keys=True).encode("utf-8")).hexdigest()
                data[component].append(
                    {component_name: item[component_name], 'hash': item_hash, component_id: item[component_id]})
        with open(self.original_ids_file, "w") as export_file:
            export_file.write(json.dumps(data))

    def backup_config(self):
        """
        Backup all of our application configuration

        :return: files
        """
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)

        _info('Exporting templates and hostgroups')
        self.export_component_config('template', 'templateid', 'templates',
                                     'templates')
        self.export_component_config('hostgroup', 'groupid', 'groups',
                                     'hostgroups')
        _info('Exporting hosts')
        self.export_component_config('host', 'hostid', 'hosts', 'hosts')
        _info('Exporting registration actions')
        self.export_action_config(2, 'reg_actions',
                                  'auto-registration actions')
        _info('Exporting trigger actions')
        self.export_action_config(0, 'trigger_actions',
                                  'trigger actions')
        _info('Exporting media types')
        self.export_component_config('mediatype', 'mediatypeid', 'mediaTypes', 'mediatypes')

        _info('Exporting services')
        self.export_component('service', 'services')

        _info('Exporting proxies')
        self.export_component('proxy', 'proxies')

        self.get_id_file()

    # imports
    def import_configuration(self, component):
        """
        import a JSON file backup of Zabbix components like templates or hosts

        :param component: which component to import. E.g. hosts, hostgroups,
                        templates
        """
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            try:
                self.zbx_client.confimport('json', component_data, _rules)
            except ZabbixAPIException:
                _warn('Could not import configuration for {}. Attempting manual {} update', component, component)
                if component == 'templates' and self.force_template:
                    _info('Deleting all current templates')
                    self.delete_all(component)
                else:
                    self.compare_ids(component)
                _info('Importing components')
                self.zbx_client.confimport('json', component_data, _rules)

    def import_trigger_actions(self):
        trig_actions_path = os.path.join(self.data_dir, _TRIGGER_ACTIONS_FILE)
        with open(trig_actions_path) as trigger_actions:
            # trig_actions_list = json.load(trigger_actions)
            trig_actions_list = self._remove_keys(json.load(trigger_actions), self.keys_to_remove['trigger_actions'])
            for trigger_action in trig_actions_list:
                try:
                    self.zbx_client.action.create(trigger_action)
                except ZabbixAPIException as err:
                    self.zbx_client.action.update(trigger_action)

    def import_registration_actions(self):
        reg_actions_path = os.path.join(self.data_dir, _REG_ACTIONS_FILE)
        with open(reg_actions_path, 'r') as reg_actions:
            for reg_action in json.load(reg_actions):
                self._remove_keys(reg_action, self.keys_to_remove['reg_actions'])
                try:
                    self._update_ids(reg_action)
                    self.zbx_client.action.create(reg_action)
                except ZabbixAPIException:
                    self.zbx_client.action.update(reg_action)

    def import_actions(self):
        """
        import auto-registration and trigger actions from backup file

        """
        self.get_id_maps(['templates', 'hostgroups'])
        # self.original_ids = json.load(open(self.original_ids_file))
        try:
            self.zbx_client.action.delete("3")
        except ZabbixAPIException as err:
            # todo: add checking for failures when object doesn't exist
            # "pyzabbix.ZabbixAPIException: ('Error -32500: Application error.,
            # No permissions to referred object or it does not exist!', -32500)"
            _warn(str(err))
        _info('Importing trigger actions')
        self.import_trigger_actions()
        _info('Importing registration actions')
        self.import_registration_actions()

    def compare_ids(self, component):
        """
        Compare the ids and hashes of components for imported configuration.
        Remove any components that are in the destination server but not in the imported configuration
        :param component: Which component to compare the data of
        """

        component_id = self.id_mapping[component]['id']
        ids_to_delete = []
        for item in self.original_ids[component]:
            import_id = item[component_id]
            if import_id in self.dest_ids[component] and item["hash"] != self.dest_ids[component][import_id]['hash']:
                ids_to_delete.append(import_id)

        for del_id in list(ids_to_delete):
            _info("Deleting '{}' id: {}", component, del_id)
            getattr(self.zbx_client, self.id_mapping[component]['api_name']).delete(del_id)

    def delete_all(self, component):
        for item_id in self.dest_ids[component].keys():
            getattr(self.zbx_client, self.id_mapping[component]['api_name']).delete(item_id)

    def import_components(self, component):
        """
        Method for importing components which cannot be configured using a configuration import.
        If the component exists in destination server it is updated
        :param component: Component to import
        """
        import_file = '{}/{}.json'.format(self.data_dir, component)
        component_method = self.id_mapping[component]['api_name']
        file = open(import_file).read()
        if os.path.isfile(import_file):
            for item in json.loads(file):
                if component in self.keys_to_remove:
                    self._remove_keys(item, self.keys_to_remove[component])
                try:
                    getattr(self.zbx_client, component_method).create(item)
                except ZabbixAPIException:
                    getattr(self.zbx_client, component_method).update()

    def get_id_maps(self, components):
        """
        Query Zabbix server to get specified objects.
        These are added to map, with structure {component: {id: (name/host, hash), id: (...), ...}, component: ... }
        :param components: list of components to get id maps for
        :return: map of components.
        """
        for component in components:
            component_id = self.id_mapping[component]['id']
            component_name = self.id_mapping[component]['name']
            for item in getattr(self.zbx_client, self.id_mapping[component]['api_name']).get(output="extend"):
                data = dict(item)
                del data[component_id]
                item_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
                self.dest_ids[component][item[component_id]] = {'name': item[component_name], 'hash': item_hash,
                                                                'id': item[component_id]}
        self.original_ids = json.load(open(self.original_ids_file)) if self.original_ids == {} else self.original_ids

    def _update_ids(self, reg_action):
        """
        take a registration action object and recurse into the data to look for
        IDs which need updating and update them to the new ID of the equivalent
        hostgroup or template after being imported.
        :param reg_action: JSON of Zabbix registration action
        """
        if type(reg_action) is str:
            reg_action = json.loads(reg_action)

        if type(reg_action) is dict:
            for reg_action_key in reg_action.copy():
                if type(reg_action[reg_action_key]) in (list, dict):
                    self._update_ids(reg_action[reg_action_key])
                elif reg_action_key == 'templateid':
                    self._update_template_id(reg_action)
                elif reg_action_key == 'groupid':
                    self._update_group_id(reg_action)
                elif reg_action_key in (
                        'actionid', 'maintenance_mode', 'eval_formula',
                        'operationid'):
                    del reg_action[reg_action_key]
        elif type(reg_action) is list:
            for item in reg_action:
                if type(item) in (list, dict):
                    self._update_ids(item)
        else:
            raise TypeError
        return reg_action

    def _update_template_id(self, reg_action):
        host = None
        for template in self.original_ids["templates"]:
            if template['templateid'] == reg_action['templateid']:
                host = template['host']
        for new_template in self.dest_ids['templates']:
            if host == new_template['host']:
                reg_action['templateid'] = new_template['templateid']

    def _update_group_id(self, reg_action):
        name = None
        for group in self.original_ids["hostgroups"]:
            if group['groupid'] == reg_action['groupid']:
                name = group['name']
        for new_group in self.imported_hostgroup_ids:
            if name == new_group['name']:
                reg_action['groupid'] = new_group['groupid']

    def _remove_keys(self, data, keys_to_remove):
        if not isinstance(data, (dict, list)):
            return data
        if isinstance(data, list):
            return [self._remove_keys(value, keys_to_remove) for value in data]
        return {key: self._remove_keys(value, keys_to_remove) for key, value in data.items()
                if key not in keys_to_remove}

    def restore_config(self):
        _info('Getting current ID\'s')
        self.get_id_maps(components=['templates', 'hostgroups', 'hosts', 'mediatypes'])
        _info('Importing hostgroups')
        self.import_configuration('hostgroups')
        _info('Importing media types')
        self.import_configuration('mediatypes')
        _info('Importing templates')
        self.import_configuration('templates')
        _info('Importing hosts')
        self.import_configuration('hosts')
        _info('Importing services')
        self.import_components('services')
        _info('Importing proxies')
        self.import_components('proxies')
        _info('Importing actions')
        self.import_actions()
