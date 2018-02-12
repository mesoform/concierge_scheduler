from pyzabbix import ZabbixAPIException
import json
import os
from collections import defaultdict

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

# zabbix init
__zbx_api = None


class ZabbixAdmin:
    """

    """

    def __init__(self, zbx_client):
        """

        """
        self.zbx_client = zbx_client

    @staticmethod
    def run(action):
        action()

    # backups aka exports
    @staticmethod
    def __export_json_to_file(result, export_dir, export_filename):
        target_absolute_path = '{}/{}.json'.format(export_dir, export_filename)
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
                                       export_dir, export_filename,
                                       label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output='extend',
                                  selectOperations='extend',
                                  selectRecoveryOperations='extend',
                                  selectFilter='extend',
                                  filter={'eventsource': get_event_source})

        self.__export_json_to_file(json.dumps(results), export_dir,
                                   export_filename)

    def __get_data_and_export(self, component, get_output,
                              export_dir, export_filename,
                              label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output=get_output)

        self.__export_json_to_file(json.dumps(results), export_dir,
                                   export_filename)

    def __get_data_and_export_config(self, component, get_id_prop_name,
                                     export_option_name,
                                     export_dir, export_filename,
                                     label_for_logging=None):
        results = self.__get_data(component, label_for_logging,
                                  output=get_id_prop_name)
        print(results)
        component_ids = [component[get_id_prop_name] for component in results]

        export_options = {export_option_name: component_ids}
        print(export_options)
        result = self.zbx_client.configuration.export(options=export_options,
                                                      format='json')

        self.__export_json_to_file(result, export_dir, export_filename)

    def export_templates(self, export_dir):
        self.__get_data_and_export_config(
            'template', 'templateid', 'templates', export_dir, 'templates')

    def export_host_groups(self, export_dir):
        self.__get_data_and_export_config(
            'hostgroup', 'groupid', 'groups', export_dir, 'hostgroups')

    def export_hosts(self, export_dir):
        self.__get_data_and_export_config('host', 'hostid', 'hosts', export_dir,
                                          'hosts')

    def export_media_types(self, export_dir):
        self.__get_data_and_export('mediatype', 'extend', export_dir,
                                   'mediatypes')

    def export_auto_registration_actions(self, export_dir):
        self.__get_selected_data_and_export(
            'action', 2, export_dir, 'reg_actions', 'auto-registration actions')

    def export_trigger_actions(self, export_dir):
        self.__get_selected_data_and_export(
            'action', 0, export_dir, 'trigger_actions', 'trigger actions')

    def export_actions_data(self, export_dir):
        data = defaultdict(list)

        for template in self.zbx_client.template.get(output="extend"):
            templates = \
                {"templateid": template['templateid'], "host": template['host']}
            data['templates'].append(templates)

        for hostgroup in self.zbx_client.hostgroup.get(output="extend"):
            hostgroups = {"groupid": hostgroup['groupid'],
                          "name": hostgroup['name']}
            data['hostgroups'].append(hostgroups)

        target_path = '{}/actions_data_orig.json'.format(export_dir)
        with open(target_path, "w") as export_file:
            export_file.write(json.dumps(data))

    def backup_app(self, export_dir):
        if not os.path.isdir(export_dir):
            os.makedirs(export_dir)

        for export_fn in [
            self.export_templates,
            self.export_host_groups,
            self.export_hosts,
            self.export_media_types,
            self.export_auto_registration_actions,
            self.export_trigger_actions,
            self.export_actions_data
        ]:
            export_fn(export_dir)

    # imports

    def __import_objects(self, component, import_dir):
        import_file = '{}/{}.json'.format(import_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            try:
                self.zbx_client.confimport('json', component_data, _rules)
            except ZabbixAPIException as err:
                print(err)

    def __import_reg_actions(self, component, import_dir):
        import_file = '{}/{}.json'.format(import_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            actions = json.loads(component_data)
            for action in actions:
                self.zbx_client.action.create(action)

    def __import_trig_actions(self, component, import_dir):
        self.zbx_client.action.delete("3")
        import_file = '{}/{}.json'.format(import_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            trig_actions = json.loads(component_data)
            for action in trig_actions:
                self.zbx_client.action.create(action)

    def __import_media_types(self, component, import_dir):
        self.zbx_client.mediatype.delete("1", "2", "3")
        import_file = '{}/{}.json'.format(import_dir, component)
        with open(import_file, 'r') as f:
            component_data = f.read()
            # __info('Importing {}...', component)
            mediatypes = json.loads(component_data)
            for mediatype in mediatypes:
                self.zbx_client.mediatype.create(mediatype)

    def import_hostgroups(self, import_dir):
        self.__import_objects('hostgroups', import_dir)

    def import_templates(self, import_dir):
        self.__import_objects('templates', import_dir)

    def import_hosts(self, import_dir):
        self.__import_objects('hosts', import_dir)

    def import_reg_actions(self, import_dir):
        self.__import_reg_actions('reg_actions_import', import_dir)

    def import_trig_actions(self, import_dir):
        self.__import_trig_actions('trigger_actions_import', import_dir)

    def import_mediatypes(self, import_dir):
        self.__import_media_types('mediatypes', import_dir)

    @staticmethod
    def import_comp(import_dir, components):
        for import_fn in components:
            import_fn(import_dir)

    def exp_act_data_dest(self, export_dir):
        data = defaultdict(list)

        for template in self.zbx_client.template.get(output="extend"):
            templates = {"templateid": template['templateid'],
                         "host": template['host']}
            data['templates'].append(templates)

        for hostgroup in self.zbx_client.hostgroup.get(output="extend"):
            hostgroups = {"groupid": hostgroup['groupid'],
                          "name": hostgroup['name']}
            data['hostgroups'].append(hostgroups)

        target_path = '{}/actions_data_dest.json'.format(export_dir)
        with open(target_path, "w") as export_file:
            export_file.write(json.dumps(data))

    def get_all(self, act_line, key, orig, dest):
        if type(act_line) == str:
            act_line = json.loads(act_line)
        if type(act_line) is dict:
            for actjsonkey in act_line.copy():
                if type(act_line[actjsonkey]) in (list, dict):
                    self.get_all(act_line[actjsonkey], key, orig, dest)
                elif actjsonkey == key:
                    if key == 'templateid':
                        for tmplorig in orig["templates"]:
                            if tmplorig['templateid'] == act_line[actjsonkey]:
                                hostorig = tmplorig['host']
                                for tmpldest in dest["templates"]:
                                    if hostorig == tmpldest['host']:
                                        act_line[actjsonkey] = tmpldest[
                                            'templateid']
                    elif key == 'groupid':
                        for grporig in orig["hostgroups"]:
                            if grporig['groupid'] == act_line[actjsonkey]:
                                hostorig = grporig['name']
                                for grpdest in dest["hostgroups"]:
                                    if hostorig == grpdest['name']:
                                        act_line[actjsonkey] = grpdest[
                                            'groupid']
                                break
                elif actjsonkey != key:
                    if actjsonkey in (
                            'actionid', 'maintenance_mode', 'eval_formula',
                            'operationid'):
                        del act_line[actjsonkey]
        elif type(act_line) is list:
            for item in act_line:
                if type(item) in (list, dict):
                    self.get_all(item, key, orig, dest)

    def gen_imp_reg_act_file(self, files_dir):
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
            self.get_all(act_line, 'groupid', orig, dest)
            self.get_all(act_line, 'templateid', orig, dest)

        target_path = '{}/reg_actions_import.json'.format(files_dir)
        with open(target_path, "w") as export_file:
            export_file.write(json.dumps(data))

        actions_data.close()

    def remove_keys(self, data):
        if not isinstance(data, (dict, list)):
            return data
        if isinstance(data, list):
            return [self.remove_keys(value) for value in data]
        return {key: self.remove_keys(value) for key, value in data.items()
                if key not in {'actionid', 'maintenance_mode', 'eval_formula',
                               'operationid'}}

    def gen_imp_trig_act_file(self, files_dir):
        actions_file = '{}/trigger_actions.json'.format(files_dir)
        actions_json = open(actions_file)
        trigger_actions = json.load(actions_json)
        data = self.remove_keys(trigger_actions)

        target_path = '{}/trigger_actions_import.json'.format(files_dir)
        with open(target_path, "w") as export_file:
            export_file.write(json.dumps(data))

        actions_json.close()

    def import_app(self, import_dir):
        to_import = [
            self.import_hostgroups,
            self.import_templates,
            self.import_hosts
        ]
        self.import_comp(import_dir, to_import)
        self.exp_act_data_dest(import_dir)
        self.gen_imp_reg_act_file(import_dir)
        to_import = [
            self.import_reg_actions
        ]
        self.import_comp(import_dir, to_import)
        self.gen_imp_trig_act_file(import_dir)
        to_import = [
            self.import_trig_actions
        ]
        self.import_comp(import_dir, to_import)
        to_import = [
            self.import_mediatypes
        ]
        self.import_comp(import_dir, to_import)
