import requests
from requests.exceptions import RequestException
import argparse, json, os 
from time import sleep as _sleep
import yaml
import jinja2
import pprint
import sys

#example curl calls 
"""
curl -X POST -d'username=admin&password=striim' http://localhost:9080/security/authenticate
curl --request GET --url http://localhost:9080/api/v2/applications --header 'Accept: application/json' --header 'Authorization:STRIIM-TOKEN 01ef58e8-1c83-ee81-944e-1e637dbe91f9'
curl --request GET --url http://localhost:9080/api/v2/applications/templates --header 'Accept: application/json' --header 'Authorization: STRIIM-TOKEN 01ef5903-aed5-19b1-84a1-6e164372c877'
curl -X POST http://localhost:9080/api/v2/applications/HomeDepot.app_cdc_pos_training_data/deployment
"""

#example calls of this program 
"""
-- example call for fetching a template json based on source and target adapters
python3 StriimAPI.py -gt '{"sourceAdapter":"OracleReader", "targetAdapter": "SpannerWriter", "applicationName":"app_oracle_spanner_cdc"}'

-- example call to create an application using template json file 
python3 StriimAPI.py -ca template.json

-- example call for deploying an existing application 
python3 StriimAPI.py -d --app_name 'HomeDepot.app_cdc_pos_training_data' --deployment_options '{"deploymentGroupName": "default","deploymentType": "ANY", "flows": [ {"flowName": "HomeDepot.app_cdc_pos_training_data_SourceFlow","deploymentGroupName": "default","deploymentType": "ANY"}]}'

-- example call to list the objects in Striim
python3 StriimAPI.py -rt list_objects.tql

"""

class VerboseStore(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(f"Storing {values} in the {option_string} option...")
        setattr(namespace, self.dest, values)

# module level functions
def define_argsparser():
    parser = argparse.ArgumentParser()
    #parser.add_argument("-n", "--name", action=VerboseStore)
    parser.add_argument("-gt", "--get_template", dest='template_details_json', type=json.loads, default={}, action=VerboseStore)
    parser.add_argument("-ca", "--create_application_from_json",help="enter the full path of the JSON template file", type=str, action=VerboseStore)
    parser.add_argument("-rt", "--run_tql", dest='tql_file_name',help="enter the full path of the TQL file",type=str,action=VerboseStore)
    parser.add_argument("-l", "--list_applications", action="store_true") 
    parser.add_argument("-status", "--status", action="store_true")
    parser.add_argument("-start", "--start_app", action="store_true")
    parser.add_argument("-stop", "--stop_app", action="store_true")
    parser.add_argument("-u", "--undeploy_app", action="store_true")
    parser.add_argument("-d", "--deploy_app", action="store_true")
    parser.add_argument("-a", "--app_name", help="enter the application name", type=str, action=VerboseStore) 
    parser.add_argument("-dopt", "--deployment_options", help="enter applicaion specific deployment options", type=str, action=VerboseStore) 
    args = parser.parse_args()
    return args 

class AuthErr(Exception):
    pass

class StriimAPI(object):
    
    def __init__(self, url, install_type='on_prem', passphrase='striim'):
        self.url = url
        self.install_type = install_type 
        # Various Striim API URLs
        self.login_url = self.url + "/security/authenticate"
        self.applications_url = self.url + "/api/v2/applications"
        self.tungsten_url = self.url + f"/api/v2/tungsten/?passphrase={passphrase}"

    def get_token(self, params):
        if self.install_type == 'on_prem':
            return self.get_token_on_prem(params['username'], params['password'])
        elif self.install_type == 'cloud':
            return params['api_key']

    def get_token_on_prem(self, username, password):
        payload = {'username': username, 'password': password}
        try:
            url = self.login_url 
            resp = requests.post(url, data=payload)
            if resp.status_code != 200:
                raise AuthErr('Likely: wrong username / password.')
            tokenjson = json.loads(resp.text)
            return tokenjson["token"]
        except RequestException as ex:
            raise ex
        
    #Function to Generate API Call Headers
    def get_header(self, auth_token, content_type):
        headers = {
           "Authorization": 'STRIIM-TOKEN ' + str(auth_token),
           "Content-Type": content_type
        }
        return headers
    
    #Function to get the list of applications 
    def get_applications_list(self, token):
        try:
            headers = self.get_header(token, 'application/json')
            get_status_response = requests.get(self.applications_url, headers=headers)
            app_list_resp = get_status_response.json()
            print(app_list_resp)
            return app_list_resp
        except requests.exceptions.HTTPError as errval:
            raise SystemExit(errval)

    #Function to get status of application
    def status_application(self, token, app_name):
        try:
            headers = self.get_header(token, 'application/json')
            get_status_response = requests.get(self.applications_url + f"/{app_name}", headers=headers)
            status = get_status_response.json()['status']
            print("Current application status = {}".format(status))
            return status
        except requests.exceptions.HTTPError as errval:
            raise SystemExit(errval)
    
    #Function to start the striim application
    def start_application(self, token, app_name):
        try:
            headers = self.get_header(token, 'application/json')
            response = requests.post(self.applications_url + f"/{app_name}/sprint", headers=headers)
            print(f"start_application response: {response.json()} ")
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        
    #Function to stop the striim application
    def stop_application(self, token, app_name ):
        try:
            headers = self.get_header(token, 'application/json')
            response = requests.delete(self.applications_url + f"/{app_name}/sprint", headers=headers)
            print(f"stop_application response: {response.json()} ")
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        
    #Function To Deploy Application
    def deploy_application(self, token, app_name, data='{"deploymentGroupName": "default","deploymentType": "ANY", "flows": []}'):
        try:
            headers = self.get_header(token, 'application/json')
            deployment_url = self.applications_url + f"/{app_name}/deployment"
            print(deployment_url) 
            deploy_export = requests.post(deployment_url,data=data,headers=headers)
            if deploy_export.status_code == 200:
                print("Application deployed successfully")
            else:
                print("Application deployed failed")
                print(deploy_export.text)
                deploy_export.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

    #Function to undeploy application
    def undeploy_application(self, token, app_name):
        try:
            retry = 0
            while retry < 3:
                status = self.status_application(token,app_name)
                retry = retry + 1
                if status == "STOPPING":
                    print("Still Stopping - Waiting for 20 Secs")
                    _sleep(20)
                else:
                    break
            headers = self.get_header(token, 'application/json')
            response = requests.delete(self.applications_url + f"/{app_name}/deployment",
                                    headers=headers)
            print("undeploy_application response {} ".format(response))
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        
    def get_template_details(self, token, templateid, path='/api/v2/applications/templates'):
        headers = self.get_header(token, 'application/json')
        """
        headers = {
            "Accept": "application/json",
            "Authorization": 'STRIIM-TOKEN ' + token,
            "Content-Type": "application/json"
        }
        """
        try:
            url = self.url + path + '/' + templateid
            #url = self.url + path 
            # Use json=payload to serialize automatically
            #print(url)
            resp = requests.get(url, headers=headers)
            print(resp.text)
            print(resp.status_code)
            if resp.status_code != 200:
                raise AuthErr('Failed to get template details.')
            return resp.text
        except RequestException as ex:
            raise ex
        
    def get_template_defn(self, token, sourceAdapter, targetAdapter, path='/api/v2/applications/templates/definition'):
        payload = {"sourceAdapter":sourceAdapter,"targetAdapter":targetAdapter}
        headers = self.get_header(token, 'application/json')
        try:
            url = self.url + path
            #url = self.url + path 
            # Use json=payload to serialize automatically
            #print(url)
            resp = requests.post(url, headers=headers, json=payload)
            print(resp.text)
            print(resp.status_code)
            if resp.status_code != 200:
                raise AuthErr('Failed to get template definition.')
            return resp.text
        except RequestException as ex:
            raise ex

    def create_application(self, token, payload, path='/api/v2/applications'):
        headers = self.get_header(token, 'application/json') 
        try:
            url = self.url + path
            # Use json=payload to serialize automatically
            #print(url)
            print(payload)
            resp = requests.post(url, headers=headers, json=payload)
            print(resp.text)
            print(resp.status_code)
            if resp.status_code != 200:
                raise AuthErr('Failed to create application.')
            return resp.text
        except RequestException as ex:
            raise ex
        
    def gen_template_json(self, template, application_name, source_adapter, target_adapter):
        out_dict = {
            "templateDefinition": {
                "sourceAdapter": source_adapter,
                "targetAdapter": target_adapter
                },
            "applicationName": application_name 
        }
        for k in template:
            if isinstance(k, str):
                out_dict[k] = {}
                for j in template[k]:
                    if 'name' in j:
                        out_dict[k][j['name']] = None
        #print(out_dict) 
        return out_dict 
    
    def run_tql_file(self, token, file_name, jinja_params={}, je=None):
        try:
            with open(file_name,"r") as f:
                raw_data = f.read()
                data = raw_data 
                if (je and jinja_params):
                    template = je.from_string(data)
                    data = template.render(jinja_params)
                headers = self.get_header(token, 'text/plain')
                print(data)
                response = requests.post(self.tungsten_url, headers=headers, data=data)
                if response.status_code == 200:
                    print(f"TQL File {file_name} executed successfully")
                    pprint.pprint(json.loads(response.text), compact=True) 
                else:
                    print(f"Failure encounterd while running the TQL file {file_name}: {response.text}")
                    response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

if __name__ == '__main__':
    # set required variables and get api token

    je = jinja2.Environment()

    with open('striim_config.yaml', 'r') as file:
        striim_config = yaml.safe_load(file)

    print(striim_config)
    striim_install_type = striim_config['striim_install_type']
    url = ''
    api_params = {}
    if striim_install_type == 'on_prem':
        api_params['username'] = striim_config[striim_install_type]['striim_username']
        api_params['password'] = striim_config[striim_install_type]['striim_password']
        url = striim_config[striim_install_type]['striim_url']
    elif striim_install_type == 'cloud':
        api_params['api_url'] = striim_config[striim_install_type]['api_url']
        api_params['api_key'] = striim_config[striim_install_type]['api_key']
        url = api_params['api_url']
    striimapi = StriimAPI(url, install_type=striim_install_type)
    token = striimapi.get_token(api_params)
    print(token)
    #sys.exit(0)

    # sample call to this program with arguments: python3 StriimAPI.py -gt '{"sourceAdapter":"OracleReader", "targetAdapter": "SpannerWriter"}' 
    # define argument parser
    args = define_argsparser()
    print(args.template_details_json)

    # Test code for fetching templates and writing it out to JSON files. 
    # In the JSON file generated, please set all fields to null for which you want to use default values in Striim 
    # for example: set ReturnDateTimeAs to null if you want Striim's default handling to work
    if args.template_details_json:
        print('inside if args.template_details_json')
        #path = '/api/v2/applications/templates/definition'
        source_adapter = args.template_details_json.get('sourceAdapter','')
        target_adapter = args.template_details_json.get('targetAdapter','')
        application_name = args.template_details_json.get('applicationName')
        #print(f"app_name: {application_name}") 
        output_file = args.template_details_json.get('outputFileName', os.path.join(os.getcwd(),'templates/generated',f"{source_adapter}-{target_adapter}.json"))
        print(output_file)

        if not source_adapter:
            raise RuntimeError("sourceAdapter is required, please specify a valid sourceAdapter")
        
        if not target_adapter:
            raise RuntimeError("targetAdapter is required, please specify a valid targetAdapter")

        if not application_name:
            raise RuntimeError("applicationName is required, please specify a valid name")

        sample_template = striimapi.get_template_defn(token,source_adapter,target_adapter) 
        output_dict = striimapi.gen_template_json(json.loads(sample_template), application_name, source_adapter, target_adapter)
        #print(output_dict)
        with open(output_file,"w") as outf:
            outf.write(json.dumps(output_dict))

    # Create Application
    # Load json file
    if args.create_application_from_json:
        #path = '/api/v2/applications'
        with open(args.create_application_from_json) as f:
            payload = json.load(f)
            print(payload)
            striimapi.create_application(token, payload)

    # get list of applications
    if args.list_applications:
            striimapi.get_applications_list(token)

    # get status of application 
    if args.status:
        if args.app_name:
            striimapi.status_application(token,args.app_name)
        else:
           raise RuntimeError("applicationName is required, please specify a valid name by using --app_name <app_name>") 

    # start application
    if args.start_app:
        if args.app_name:
            striimapi.start_application(token,args.app_name)
        else:
           raise RuntimeError("applicationName is required, please specify a valid name by using --app_name <app_name>") 
        
    # start application
    if args.stop_app:
        if args.app_name:
            striimapi.stop_application(token,args.app_name)
        else:
           raise RuntimeError("applicationName is required, please specify a valid name by using --app_name <app_name>") 

    # undeploy application
    if args.undeploy_app:
        if args.app_name:
            striimapi.undeploy_application(token,args.app_name)
        else:
           raise RuntimeError("applicationName is required, please specify a valid name by using --app_name <app_name>") 
        
    # deploy application
    if args.deploy_app:
        if (args.app_name and args.deployment_options):
            striimapi.deploy_application(token,args.app_name, args.deployment_options)
        else:
           raise RuntimeError("applicationName is required, please specify a valid name by using --app_name <app_name>") 

    # run tql file
    if args.tql_file_name:
        striimapi.run_tql_file(token,args.tql_file_name, striim_config, je)