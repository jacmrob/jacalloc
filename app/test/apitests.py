import unittest
import requests
import uuid
import json
import time

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_CONFLICT = 409
HTTP_NOT_FOUND = 404
HTTP_NO_CONTENT = 204
HTTP_PRECONDITION_FAILED = 412


class TestCreateApi(unittest.TestCase):
    """Class for testing basic resource create/destroy functionality.
    Must run before TestDependentApi to ensure we can create/destroy resources to test with."""

    def setUp(self):
        self.base_url = 'http://localhost:5000/'
        self.base_url_resources = self.base_url + 'resources'
        self.resource_name = "testapi" + str(uuid.uuid1())[:15]
        self.create_body = {"ip": "0.0.0.0",
                            "project": "apitests",
                            "in_use": False}
        self.headers = {"Content-Type": "application/json"}

    def create_record_body(self):
        body = self.create_body.copy()
        body["name"] = "testallocatorapi-" + str(uuid.uuid1())[:15]
        return body

    def test_health(self):
        response = requests.get(self.base_url)
        self.assertEqual(response.status_code, HTTP_OK)

    def test_resource_create_and_delete(self):
        create = self.create_record_body()
        response = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(create))
        self.assertEqual(response.status_code, HTTP_CREATED)
        time.sleep(5)
        delete = requests.delete(self.base_url_resources + "/" + create["name"], headers=self.headers)
        self.assertEqual(delete.status_code, HTTP_NO_CONTENT)

    def test_resource_create_empty_body(self):
        response = requests.post(self.base_url_resources, headers=self.headers, data={})
        self.assertEqual(response.status_code, HTTP_BAD_REQUEST)

    def test_resource_create_missing_attribute(self):
        bad_body = self.create_record_body()
        del bad_body["name"]
        response = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(bad_body))
        self.assertEqual(response.status_code, HTTP_BAD_REQUEST)

    def test_resource_create_bad_json(self):
        bad_body = self.create_record_body()
        bad_body["in_use"] = "a string"
        response = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(bad_body))
        self.assertEqual(response.status_code, HTTP_BAD_REQUEST)

    def test_resource_create_when_already_exists(self):
        create = self.create_record_body()
        _ = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(create))
        response2 = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(create))
        self.assertEqual(response2.status_code, HTTP_CONFLICT)
        delete = requests.delete(self.base_url_resources + "/" + create["name"], headers=self.headers)
        self.assertEqual(delete.status_code, HTTP_NO_CONTENT)


class TestDependentApi(unittest.TestCase):
    """
    This test suite assumes we can successfully create and delete resources.
    """
    @classmethod
    def setUpClass(cls):
        cls.base_url = 'http://localhost:5000/'
        cls.base_url_resources = cls.base_url + 'resources'
        cls.resource_name = "testallocatorapi-" + str(uuid.uuid1())[:15]
        cls.project = 'apitests'
        cls.create_body = {"name": cls.resource_name,
                            "ip": "0.0.0.0",
                            "project": cls.project,
                            "in_use": False}
        cls.headers = {"Content-Type": "application/json"}
        init_resp = requests.post(cls.base_url_resources, data=json.dumps(cls.create_body), headers=cls.headers)
        assert init_resp.status_code == HTTP_CREATED

    def setUp(self):
        self.base_url_resources = TestDependentApi.base_url_resources
        self.headers = TestDependentApi.headers
        self.project = TestDependentApi.project
        self.resource_name = TestDependentApi.resource_name
        self.create_body = TestDependentApi.create_body

    @classmethod
    def tearDownClass(cls):
        delete_resp = requests.delete(cls.base_url_resources + "/" + cls.resource_name)
        assert delete_resp.status_code == HTTP_NO_CONTENT

    def create_record_body(self):
        body = self.create_body.copy()
        body["name"] = "testallocatorapi-" + str(uuid.uuid1())[:15]
        return body

    def assert_record_is_in_list(self, r_list, r_name):
        for r in r_list:
            if r["name"] == r_name:
                return True
        return False

    # GET /resources
    def test_get_resources(self):
        resp = requests.get(self.base_url_resources, headers=self.headers)
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assert_record_is_in_list(resp.json(), self.resource_name)

    def test_get_resources_bad_proj(self):
        resp = requests.get(self.base_url_resources, headers=self.headers, params={"project": "not-a-real-proj"})
        self.assertEqual(resp.json(), [])
        self.assertEqual(resp.status_code, HTTP_OK)

    def test_get_resources_multiple(self):
        new_body = self.create_record_body()
        create = requests.post(self.base_url_resources, headers=self.headers, data=json.dumps(new_body))
        self.assertEqual(create.status_code, HTTP_CREATED)

        list = requests.get(self.base_url_resources, headers=self.headers)
        self.assertEqual(list.status_code, HTTP_OK)
        self.assertGreaterEqual(len(list.json()), 2)

        delete = requests.delete(self.base_url_resources + "/" + new_body["name"], headers=self.headers)
        self.assertEqual(delete.status_code, HTTP_NO_CONTENT)

    # GET /resources/<name>
    # 200
    def test_get_resource(self):
        resp = requests.get(self.base_url_resources + "/" + self.resource_name, headers=self.headers)
        self.assertEqual(resp.json()["name"], self.resource_name)
        self.assertEqual(resp.json()["project"], self.create_body["project"])
        self.assertEqual(resp.status_code, HTTP_OK)

    def test_get_resource_with_project(self):
        resp = requests.get(self.base_url_resources + "/" + self.resource_name, headers=self.headers, params={"project": self.project})
        self.assertEqual(resp.json()["name"], self.resource_name)
        self.assertEqual(resp.json()["project"], self.create_body["project"])
        self.assertEqual(resp.status_code, HTTP_OK)

        # 404
    def test_get_resource_not_found(self):
        resp = requests.get(self.base_url_resources + "/not-a-real-resource", headers=self.headers)
        self.assertEqual(resp.status_code, HTTP_NOT_FOUND)

    def test_get_resource_bad_proj(self):
        resp = requests.get(self.base_url_resources + "/" + self.resource_name, headers=self.headers, params={"project": "not-a-real-proj"})
        self.assertEqual(resp.status_code, HTTP_NOT_FOUND)

    # GET /resources/name/<keyword>
    def test_get_resource_by_keyword(self):
        resp = requests.get(self.base_url_resources + "/name/testallocatorapi", headers=self.headers)
        self.assert_record_is_in_list(resp.json(), self.resource_name)

    def test_get_resource_by_keyword_none(self):
        resp = requests.get(self.base_url_resources + "/name/nonexistantasdfjhkjsh", headers=self.headers)
        self.assertEqual(resp.json(), [])
        self.assertEqual(resp.status_code, HTTP_OK)

    # POST /resources/<name>
    def test_update_resource(self):
        resp = requests.post(self.base_url_resources + "/" + self.resource_name, headers=self.headers, data=json.dumps({"usable": True}))
        self.assertEqual(resp.status_code, HTTP_OK)
        self.assertTrue(resp.json()["usable"])

    def test_update_resource_not_allowed_to_update(self):
        resp = requests.post(self.base_url_resources + "/" + self.resource_name, headers=self.headers, data={"name": "new-name"})
        self.assertEqual(resp.status_code, HTTP_BAD_REQUEST)

    def test_update_resource_empty_body(self):
        resp = requests.post(self.base_url_resources + "/" + self.resource_name, headers=self.headers, data={})
        self.assertEqual(resp.status_code, HTTP_BAD_REQUEST)

    def test_update_resource_bad_type(self):
        resp = requests.post(self.base_url_resources + "/" + self.resource_name, headers=self.headers, data=json.dumps({"in_use": "not-bool"}))
        self.assertEqual(resp.status_code, HTTP_BAD_REQUEST)

    def test_update_resource_not_found(self):
        resp = requests.post(self.base_url_resources + "/fake-resource", headers=self.headers, data=json.dumps({"usable": True}))
        self.assertEqual(resp.status_code, HTTP_NOT_FOUND)

    # POST /resources/allocate

    def free(self, resource, free_status=HTTP_OK):
        undo = requests.post(self.base_url_resources + "/" + resource["name"], headers=self.headers, data=json.dumps({"in_use": False}))
        self.assertEqual(undo.status_code, free_status)

    def allocate(self, name, parameters={}, allocate_status=HTTP_OK):
        # make sure resource is marked as usable
        resp1 = requests.post(self.base_url_resources + "/" + name, headers=self.headers, data=json.dumps({"usable": True}))
        self.assertEqual(resp1.status_code, HTTP_OK)
        self.assertTrue(resp1.json()["usable"])

        resp2 = requests.post(self.base_url_resources + "/allocate", params=parameters)
        self.assertEqual(resp2.status_code, allocate_status)
        r = None
        if allocate_status == HTTP_OK:
            self.assertTrue(resp2.json()["in_use"])
            r = resp2.json()
        return r

    def allocate_and_free(self, name, parameters={}, allocate_status=HTTP_OK, free_status=HTTP_OK):
        allocated = self.allocate(name, parameters=parameters, allocate_status=allocate_status)
        if allocated:
            self.free(allocated, free_status=free_status)

    def test_allocate_resource(self):
        self.allocate_and_free(self.resource_name)

    def test_allocate_within_a_project(self):
        self.allocate_and_free(self.resource_name, parameters={"project": self.project})

    def test_allocate_within_false_project(self):
        self.allocate_and_free(self.resource_name, parameters={"project": "not-a-real-proj"}, allocate_status=HTTP_PRECONDITION_FAILED)

    # def test_allocate_resource_no_resources(self):
    #     r = requests.get(self.base_url_resources, params={"in_use": False}).json()
    #     allocated = []
    #     while r:
    #         allocated.append(self.allocate(r.pop()["name"]))
    #         r = requests.get(self.base_url_resources, params={"in_use": False}).json()
    #     self.allocate(self.resource_name, allocate_status=HTTP_PRECONDITION_FAILED)
    #     self.free(allocated)

    def test_timed_out_list(self):
        allocated = self.allocate(self.resource_name)
        time.sleep(7)
        timed_out = requests.get(self.base_url_resources + "/allocate/timeout", params={"project": self.project, "timeout": 4})
        self.assert_record_is_in_list(timed_out.json(), allocated["name"])
        self.free(allocated)


class TestCreateApiGcloud(TestCreateApi):

    def setUp(self):
        self.base_url = 'http://localhost:5000/'
        self.base_url_resources = self.base_url + 'resources'
        self.create_body = {"tags": ["jacalloc-tests"],
                            "project": "broad-dsde-dev",
                            "in_use": False,
                            "zone": "us-central1-a"}
        self.headers = {"Content-Type": "application/json"}


class TestDependentApiGcloud(TestDependentApi):

    @classmethod
    def setUpClass(cls):
        cls.base_url = 'http://localhost:5000/'
        cls.base_url_resources = cls.base_url + 'resources'
        cls.headers = {"Content-Type": "application/json"}
        cls.project = "broad-dsde-dev"
        cls.resource_name = "testallocatorapi-" + str(uuid.uuid1())[:15]
        cls.create_body = {"name": cls.resource_name,
                        "tags": ["jacalloc-tests"],
                        "project": cls.project,
                        "in_use": False,
                        "zone": "us-central1-a"}

        init_resp = requests.post(cls.base_url_resources, data=json.dumps(cls.create_body), headers=cls.headers)
        assert init_resp.status_code == HTTP_CREATED

    def setUp(self):
        self.base_url_resources = TestDependentApiGcloud.base_url_resources
        self.headers = TestDependentApiGcloud.headers
        self.project = TestDependentApiGcloud.project
        self.resource_name = TestDependentApiGcloud.resource_name
        self.create_body = TestDependentApiGcloud.create_body


if __name__ == '__main__':
    unittest.main()
