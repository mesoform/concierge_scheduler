from pyzabbix import ZabbixAPIException
import json
import os
from collections import defaultdict

_ORIGINAL_IDS_FILE = 'original_ids_map.json'
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


class ZabbixAdmin:
    """
    Class for administering common operational activities for a Zabbix instance

    """

    def __init__(self, zbx_client, data_dir):
        """

        """
        self.zbx_client = zbx_client
        self.imported_template_ids = []
        self.imported_hostgroup_ids = []
        self.original_ids = {}
        self.data_dir = data_dir
        self.original_ids_file = '{}/{}'.format(self.data_dir,
                                                _ORIGINAL_IDS_FILE)

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
        # if not label_for_logging:
        # label_for_logging = '{}s'.format(component)
        # __info('Exporting {}...', label_for_logging)
        # getattr is like concatenating component onto the object.
        # In this case ZabbixAPI.template
        results = getattr(self.zbx_client, component).get(**kwargs)
        if not results:
            # __info('No {} found', label_for_logging)
            return
        print(results)
        return results

    def __get_selected_data_and_export(self, component, get_event_source,
                                       export_filename,
                                       label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output='extend',
                                  selectOperations='extend',
                                  selectRecoveryOperations='extend',
                                  selectFilter='extend',
                                  filter={'eventsource': get_event_source})

        self.__export_json_to_file(json.dumps(results), export_filename)

    def __get_data_and_export(self, component, get_output,
                              export_filename,
                              label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output=get_output)

        self.__export_json_to_file(json.dumps(results), export_filename)

    def __get_data_and_export_config(self, component, get_id_prop_name,
                                     export_option_name,
                                     export_filename,
                                     label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output=get_id_prop_name)
        print(results)
        component_ids = [component[get_id_prop_name] for component in results]

        export_options = {export_option_name: component_ids}
        print(export_options)
        result = self.zbx_client.configuration.export(options=export_options,
                                                      format='json')

        self.__export_json_to_file(result, export_filename)

    def get_simple_id_map(self):
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
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)

        self.__get_data_and_export_config('template', 'templateid', 'templates',
                                          'templates')
        self.__get_data_and_export_config('hostgroup', 'groupid', 'groups',
                                          'hostgroups')
        self.__get_data_and_export_config('host', 'hostid', 'hosts', 'hosts')
        self.__get_selected_data_and_export('action', 2, 'reg_actions',
                                            'auto-registration actions')
        self.__get_selected_data_and_export('action', 0, 'trigger_actions',
                                            'trigger actions')
        self.__get_data_and_export('mediatype', 'extend', 'mediatypes')
        self.get_simple_id_map()

    # imports
    def __import_objects(self, component):
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            try:
                self.zbx_client.confimport('json', component_data, _rules)
            except ZabbixAPIException as err:
                print(err)

    def __import_reg_actions(self, component):
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            actions = json.loads(component_data)
            for action in actions:
                self.zbx_client.action.create(action)

    def __import_trig_actions(self, component):
        self.zbx_client.action.delete("3")
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            trig_actions = json.loads(component_data)
            for action in trig_actions:
                self.zbx_client.action.create(action)

    def __import_media_types(self, component):
        self.zbx_client.mediatype.delete("1", "2", "3")
        import_file = '{}/{}.json'.format(self.data_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            mediatypes = json.loads(component_data)
            for mediatype in mediatypes:
                self.zbx_client.mediatype.create(mediatype)

    def import_comp(self, components):
        for import_fn in components:
            import_fn(self.data_dir)

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

    def __create_actions_file(self, actions_dict):
        target_path = '{}/{}.json'.format(self.data_dir, actions_dict)
        with open(target_path, "w") as export_file:
            export_file.write(actions_dict(self.data_dir))

    def __autoreg_action_dict(self):
        # ToDo:
        # maybe these can be one function which doesn't necessarily return
        # anything
        self.get_new_ids()
        self.original_ids = json.load(open(self.original_ids_file))

        with open('{}/reg_actions.json'.format(self.data_dir)) as reg_actions:
            for reg_action in json.load(reg_actions):
                self.__update_ids(reg_action)

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

    def remove_keys(self, data):
        if not isinstance(data, (dict, list)):
            return data
        if isinstance(data, list):
            return [self.remove_keys(value) for value in data]
        return {key: self.remove_keys(value) for key, value in data.items()
                if key not in {'actionid', 'maintenance_mode', 'eval_formula',
                               'operationid'}}

    def __trigger_action_dict(self):
        actions_file = '{}/trigger_actions.json'.format(self.data_dir)
        with open(actions_file) as actions_json:
            return self.remove_keys(json.load(actions_json))

    def restore_config(self):
        self.__import_objects('hostgroups')
        self.__import_objects('templates')
        self.__import_objects('hosts')

        self.__create_actions_file('__autoreg_action_dict')
        self.__autoreg_action_dict()
        self.__import_reg_actions('reg_actions_import')

        self.__create_actions_file('__trigger_action_dict')
        self.__import_trig_actions('__trigger_action_dict')
        self.__import_media_types('mediatypes')
