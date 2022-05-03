import json
import requests
from requests.auth import HTTPBasicAuth

from n8n.exceptions import InvalidRequestException, ResourceNotFoundException


class Client(object):
    def __init__(self, protocol=None, host=None, port=5678,
                 authentication_enabled=False, username=None, password=None):
        self.protocol = protocol or "http"
        self.host = host or "localhost"
        self.port = port

        # authentication
        self.authentication_enabled = authentication_enabled

        if authentication_enabled and not username or not password:
            raise AttributeError("Both username and password must be given")

        self.username = username
        self.password = password

        self._cookies = None
        self._login_attempts = 0

    def api_url(self, is_rest=True):
        url = f"{self.protocol}://{self.host}:{self.port}"

        return url if not is_rest else f"{url}/rest"

    def _execute(self, method, uri, data=None, is_rest=True, check_login=True):
        if check_login and not self._cookies:
            self.login()

        url = f"{self.api_url(is_rest)}{uri}" if uri.startswith("?") \
            else f"{self.api_url(is_rest)}/{uri}"

        auth = HTTPBasicAuth(self.username, self.password) \
            if self.authentication_enabled else None

        if data:
            resp = getattr(requests, method)(
                url, json=data, timeout=20, auth=auth, cookies=self._cookies)
        else:
            resp = getattr(requests, method)(
                url, timeout=10, auth=auth, cookies=self._cookies)

        if resp.status_code == 401 and self._login_attempts == 0:
            self._cookies = None
            # if it fails again, it's not due the cookie
            self._login_attempts = 1
            self._execute(method=method, uri=uri, data=data, is_rest=is_rest,
                          check_login=check_login)

        if resp.status_code == 404:
            raise ResourceNotFoundException("Resource not Found")

        if resp.status_code not in [200, 201]:
            raise InvalidRequestException(
                f"[{resp.status_code}] - {resp.json().get('message')}")

        return resp

    def post(self, uri, data, is_rest=True):
        return self._execute("post", uri, data, is_rest=is_rest)

    def get(self, uri, is_rest=True, check_login=True):
        return self._execute("get", uri, is_rest=is_rest, check_login=check_login)

    def delete(self, uri, is_rest=True):
        return self._execute("delete", uri, is_rest=is_rest)

    def patch(self, uri, data: dict = None, is_rest=True):
        return self._execute("patch", uri, data=data, is_rest=is_rest)

    def login(self):
        resp = self.get(uri="login", check_login=False)
        self._cookies = resp.cookies

        return resp

    def create_workflow(self, name: str):
        data = {
            "name": name,
            "nodes": [
                {
                    "parameters": {},
                    "name": "Start",
                    "type": "n8n-nodes-base.start",
                    "typeVersion": 1,
                    "position": [
                        250,
                        300
                    ]
                }
            ],
            "connections": {},
            "active": False,
            "settings": {},
            "tags": []
        }

        return self.post("workflows", data).json()

    def get_node_types(self):
        return self.get("node-types").json()

    def get_nodes_details(self, node_names: list):
        nodes = []

        for node_name in node_names:
            nodes.append({"name": node_name})

        return self.post("node-types", data={"nodeInfos": nodes}).json()

    def get_node_icon(self, node_name: str):
        return self.get(f"node-icon/{node_name}")

    def get_node_parameter_options(
            self, node_type: str, path: str, method: str,
            credentials: dict, current_node_parameters: dict = None):

        current_node_parameters = current_node_parameters or {}

        node_type_and_version = {"name": node_type, "version": 1}

        uri = f"node-parameter-options" \
              f"?nodeTypeAndVersion={json.dumps(node_type_and_version)}" \
              f"&path={path}&methodName={method}" \
              f"&credentials={json.dumps(credentials)}" \
              f"&currentNodeParameters={json.dumps(current_node_parameters)}"

        return self.get(uri).json()

    def get_credentials_types(self):
        return self.get("credential-types").json()

    def get_credentials(self):
        return self.get("credentials").json()

    def get_credential(self, credential_id: int, include_data=False):
        uri = f"credentials/{credential_id}"

        if include_data:
            uri += "?includeData=true"

        return self.get(uri).json()

    def delete_credential(self, credential_id: int):
        return self.delete(f"credentials/{credential_id}").json()

    def get_credential_definition(self, name: str):
        credentials = self.get("credential-types").json()["data"]

        definition = None

        for credential in credentials:
            if credential["name"] == name:
                definition = credential
                break

        return definition

    def get_workflow(self, workflow_id: int):
        return self.get(f"workflows/{workflow_id}").json()

    def get_workflows(self):
        return self.get(f"workflows").json()

    def delete_workflow(self, workflow_id: int):
        return self.delete(f"workflows/{workflow_id}").json()

    def get_executions(self, workflow_id: int, limit: int = None):
        query = {"workflowId": f"{workflow_id}"}

        uri = f"executions?filter={json.dumps(query)}"

        if limit:
            uri += f"&limit={limit}"

        return self.get(uri).json()

    def get_execution(self, execution_id: int,
                      unflatted_response: bool = False):
        uri = f"executions/{execution_id}"

        if unflatted_response:
            uri += "?unflattedResponse=true"

        return self.get(uri).json()

    def add_credentials(self, name: str, credential_type: str, nodes_access: list, data: dict):
        content = {
            "name": name,
            "type": credential_type,
            "nodesAccess": [],
            "data": data
        }

        for node in nodes_access:
            content["nodesAccess"].append(
                {
                    "nodeType": node
                }
            )

        return self.post("credentials", content).json()

    def change_credentials(
            self, credential_id: int, name: str, credential_type: str,
            nodes_access: list, data: dict):
        content = {
            "name": name,
            "type": credential_type,
            "nodesAccess": [],
            "data": data
        }

        for node in nodes_access:
            content["nodesAccess"].append(
                {
                    "nodeType": node
                }
            )

        return self.patch(f"credentials/{credential_id}", content).json()

    def activate_workflow(self, workflow_id: int):
        workflow = self.get_workflow(workflow_id)["data"]

        workflow["active"] = True

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def deactivate_workflow(self, workflow_id: int):
        workflow = self.get_workflow(workflow_id)["data"]

        workflow["active"] = False

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def update(self, workflow_id: int, nodes: list, connections: dict):
        workflow = self.get_workflow(workflow_id)["data"]

        workflow["nodes"] = nodes
        workflow["connections"] = connections

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def add_node(self, workflow_id: int, node: dict, connections: dict = None):
        workflow = self.get_workflow(workflow_id)["data"]

        workflow["nodes"].append(node)
        workflow["connections"] = connections or {}

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def change_node(self, workflow_id: int, node_name, changed_node: dict,
                    position: list = None, credentials: dict = None,
                    connections: dict = None):

        workflow = self.get_workflow(workflow_id)["data"]

        changed_nodes = []

        for original_node in workflow["nodes"]:
            original_node_name = original_node["name"]

            if original_node_name == node_name:
                # replace current node with new node, that is, edit the node

                # don't touch credentials if not given
                changed_node["credentials"] = original_node.get("credentials") \
                    if credentials is None else credentials

                # don't touch position if not given
                changed_node["position"] = original_node["position"] \
                    if position is None else position

                changed_nodes.append(changed_node)
            else:
                changed_nodes.append(original_node)

        workflow["nodes"] = changed_nodes
        workflow["connections"] = connections if connections is not None \
            else workflow["connections"]

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def execute_node(self, workflow_id: int, node_name: str, run_data: dict):
        workflow = self.get(f"workflows/{workflow_id}").json()["data"]

        content = {
            "workflowData": workflow,
            "runData": run_data,
            "startNodes": [node_name],
            "destinationNode": node_name,
        }

        return self.post("workflows/run", content).json()

    def delete_node(self, workflow_id: int, node_name: str, connections: dict,
                    deactivate=False):
        workflow = self.get_workflow(workflow_id)["data"]

        new_nodes = [
            node for node in workflow["nodes"] if node["name"] != node_name]

        workflow["active"] = not deactivate
        workflow["nodes"] = new_nodes
        workflow["connections"] = connections or {}

        return self.patch(f"workflows/{workflow_id}", data=workflow).json()

    def get_oauth2_credentials(self, url):
        resp = self.get(url)

        return resp
