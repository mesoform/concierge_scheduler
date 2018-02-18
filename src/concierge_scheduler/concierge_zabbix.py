from pyzabbix import ZabbixAPIException
import json
import os
import sys
from collections import defaultdict
import logging

_ORIGINAL_IDS_FILE = 'id_map_backup.json'
_rules = {
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


def _info(message, *args):
    __LOG.log(logging.INFO, message.format(*args))


def _log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


class ZabbixAdmin:
    """
    Class for administering common operational activities for a Zabbix instance
    """

    def __init__(self, zbx_client, data_dir):
        """
        :param zbx_client: instance of a Zabbix API client object
        :param data_dir: directory where we will keep configuration data
        """
        self.zbx_client = zbx_client
        self.imported_template_ids = []
        self.imported_hostgroup_ids = []
        self.original_ids = {}
        self.data_dir = data_dir
        self.original_ids_file = '{}/{}'.format(self.data_dir,
                                                _ORIGINAL_IDS_FILE)
        self.actions_dict = {}

    @staticmethod
    def run(action):
        action()

    # backups aka exports
    def __export_json_to_file(self, result, export_filename):
        target_absolute_path = '{}/{}.json'.format(self.data_dir,
                                                   export_filename)
        with open(target_absolute_path, "w") as export_file:
            export_file.write(result)

    def __get_data(self, component, label_for_logging=None, **kwargs):
        if not label_for_logging:
            label_for_logging = '{}s'.format(component)
        _info('Exporting {}...', label_for_logging)
        results = getattr(self.zbx_client, component).get(**kwargs)
        if not results:
            _info('No {} found', label_for_logging)
            return
        _info('results' + results, label_for_logging)
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
        results = self.__get_data('action', label_for_logging,
                                  output='extend',
                                  selectOperations='extend',
                                  selectRecoveryOperations='extend',
                                  selectFilter='extend',
                                  filter={'eventsource': event_source_id})

        self.__export_json_to_file(json.dumps(results), export_filename)

    def export_media_config(self, component,
                            export_filename,
                            label_for_logging=None):
        """
        create a JSON file backup of the Zabbix media configuration

        :param component: what media we want to export. E.g. mediatypes
        :param export_filename: the name to use for the output file
        :param label_for_logging: label we'll use when logging
        :return: file
        """
        results = self.__get_data(component, label_for_logging,
                                  output='extend')

        self.__export_json_to_file(json.dumps(results), export_filename)

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
        results = self.__get_data(component, label_for_logging,
                                  output=id_prop_name)
        print(results)
        component_ids = [component[id_prop_name] for component in results]

        export_options = {export_option_name: component_ids}
        print(export_options)
        result = self.zbx_client.configuration.export(options=export_options,
                                                      format='json')

        self.__export_json_to_file(result, export_filename)

    def get_simple_id_map(self):
        """
        we need to have a simplified map of component IDs to their names because
        when we're importing things like auto-registration actions, we need to
        know what our old and new IDs are so we can correctly link them upon
        import

        :return: file
        """
        data = defaultdict(list)

        for template in self.zbx_client.template.get(output="extend"):
            templates = \
                {"templateid": template['templateid'], "host": template['host']}
            data['templates'].append(templates)

        for hostgroup in self.zbx_client.hostgroup.get(output="extend"):
            hostgroups = {"groupid": hostgroup['groupid'],
                          "name": hostgroup['name']}
            data['hostgroups'].append(hostgroups)

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
        self.get_simple_id_map()
        _info('Exporting hosts')
        self.export_component_config('host', 'hostid', 'hosts', 'hosts')
        _info('Exporting registration actions')
        self.export_action_config(2, 'reg_actions',
                                  'auto-registration actions')
        _info('Exporting trigger actions')
        self.export_action_config(0, 'trigger_actions',
                                  'trigger actions')
        _info('Exporting media types')
        self.export_media_config('mediatype', 'mediatypes')

    # imports
    def import_components(self, component):
        """
        import a JSON file backup of Zabbix components like templates or hosts

        :param component: which component to import. E.g. hosts, hostgroups,
                        templates
        """
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            _info('Importing {}...', component)
            try:
                self.zbx_client.confimport('json', component_data, _rules)
            except ZabbixAPIException as err:
                print(err)

    def __update_actions_dict(self):
        with open('{}/reg_actions.json'.format(self.data_dir)) as reg_actions:
            for reg_action in json.load(reg_actions):
                self.actions_dict.update(self.__update_ids(reg_action))
        with open('{}/trigger_actions.json'.format(
                self.data_dir)) as actions_json:
            self.actions_dict.update(
                self.__remove_keys(json.load(actions_json)))

    def import_actions(self):
        """
        import auto-registration and trigger actions from backup file

        """
        self.get_new_ids()
        self.original_ids = json.load(open(self.original_ids_file))
        self.__update_actions_dict()
        self.zbx_client.action.delete("3")
        for action in self.actions_dict:
            self.zbx_client.action.create(action)

    def import_media_types(self, component):
        """
        import backed up media

        :param component: what media to import
        :return:
        """
        self.zbx_client.mediatype.delete("1", "2", "3")
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            _info('Importing {}...', component)
            mediatypes = json.loads(component_data)
            for mediatype in mediatypes:
                self.zbx_client.mediatype.create(mediatype)

    def get_new_ids(self):
        """
        Query Zabbix server to get a list of template/group objects and simplify
        it to a basic id:name map.
        :return: list
        """
        for template_dict in self.zbx_client.template.get(output="extend"):
            template_map = {"templateid": template_dict['templateid'],
                            "host": template_dict['host']}
            self.imported_template_ids.append(template_map)

        for hostgroup_dict in self.zbx_client.hostgroup.get(output="extend"):
            hostgroup_map = {"groupid": hostgroup_dict['groupid'],
                             "name": hostgroup_dict['name']}
            self.imported_hostgroup_ids.append(hostgroup_map)

    def __update_ids(self, reg_action):
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
                    self.__update_ids(reg_action[reg_action_key])
                elif reg_action_key == 'templateid':
                    self.__update_template_id(reg_action)
                elif reg_action_key == 'groupid':
                    self.__update_group_id(reg_action)
                elif reg_action_key in (
                        'actionid', 'maintenance_mode', 'eval_formula',
                        'operationid'):
                    del reg_action[reg_action_key]
                else:
                    raise KeyError
        elif type(reg_action) is list:
            for item in reg_action:
                if type(item) in (list, dict):
                    self.__update_ids(item)
        else:
            raise TypeError

    def __update_template_id(self, reg_action):
        for template in self.original_ids["templates"]:
            if template['templateid'] == reg_action['templateid']:
                host = template['host']
                for new_template in self.imported_template_ids:
                    if host == new_template['host']:
                        reg_action['templateid'] = new_template['templateid']

    def __update_group_id(self, reg_action):
        for group in self.original_ids["hostgroups"]:
            if group['groupid'] == reg_action['groupid']:
                name = group['name']
                for new_group in self.imported_hostgroup_ids:
                    if name == new_group['name']:
                        reg_action['groupid'] = new_group['groupid']

    def __remove_keys(self, data):
        if not isinstance(data, (dict, list)):
            return data
        if isinstance(data, list):
            return [self.__remove_keys(value) for value in data]
        return {key: self.__remove_keys(value) for key, value in data.items()
                if key not in {'actionid', 'maintenance_mode', 'eval_formula',
                               'operationid'}}

    def restore_config(self):
        _info('Importing hostgroups')
        self.import_components('hostgroups')
        _info('Importing templates')
        self.import_components('templates')
        _info('Importing hosts')
        self.import_components('hosts')
        _info('Importing actions')
        self.import_actions()
        _info('Importing media types')
        self.import_media_types('mediatypes')
