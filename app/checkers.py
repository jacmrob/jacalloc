"""
CheckRequest class and subclasses

These are for validating PUT and POST request bodies.
"""

class CheckRequest:

    def __init__(self):
        self.required_keys = ["name", "ip", "project", "in_use"]
        self.key_types = {"name": self.type_check([str, unicode]),
                          "ip": self.type_check([str, unicode]),
                          "project": self.type_check([str, unicode]),
                          "in_use": self.type_check(bool),
                          "private": self.type_check(bool),
                          "usable": self.type_check(bool)}
        self.immutable_keys = ["name", "project"]

    # takes a single type or a list of types
    def type_check(self, types):
        if type(types) == list:
            return reduce(lambda x,y: x or y, [lambda x: type(x) == y for y in types])
        return lambda x: type(x) == types

    def concat_errors(self, error_dict):
        return reduce(lambda x,y: ' ; '.join([x,y]), [k for k,v in error_dict.iteritems() if not v], "")

    def check_request_contains(self, request_dict, keys):
        return [k for k in keys if k not in request_dict.keys()]

    def check_request_does_not_contain(self, request_dict, keys):
        return [k for k in keys if k in request_dict.keys()]

    def check_request_types(self, request_dict, key_types):
        return [k for k, v in request_dict.iteritems() if k in key_types.keys() and not key_types[k](v)]

    def check_request_create(self, request_dict, required_keys=None, key_types=None):
        required_keys = required_keys or self.required_keys
        key_types = key_types or self.key_types
        missing = self.check_request_contains(request_dict, required_keys)
        bad_types = self.check_request_types(request_dict, key_types)

        errors = {"Request missing following fields: {}".format(str(missing)): len(missing) == 0,
                  "The following fields are incorrectly typed {}".format(str(bad_types)): len(bad_types) == 0}
        return self.concat_errors(errors)

    def check_request_update(self, request_dict, immutable_keys=None, key_types=None):
        immutable_keys = immutable_keys or self.immutable_keys
        key_types = key_types or self.key_types
        bad_fields = self.check_request_does_not_contain(request_dict, immutable_keys)
        bad_types = self.check_request_types(request_dict, key_types)

        errors = {"The following fields cannot be updated: {}".format(str(bad_fields)): len(bad_fields) == 0,
                  "The following fields are incorrectly typed {}".format(str(bad_types)): len(bad_types) == 0}
        return self.concat_errors(errors)


class CheckRequestGcloud(CheckRequest):

    def __init__(self):
        CheckRequest.__init__(self)
        self.key_types = {"name": CheckRequest.type_check(self, [str, unicode]),
                          "project": CheckRequest.type_check(self, [str, unicode]),
                          "zone": CheckRequest.type_check(self, [str, unicode]),
                          "in_use": CheckRequest.type_check(self, bool),
                          "ip": CheckRequest.type_check(self, [str, unicode]),
                          "private": CheckRequest.type_check(self, bool),
                          "tags": CheckRequest.type_check(self, list),
                          "disk_size": CheckRequest.type_check(self, [str, unicode]),
                          "disk_type": CheckRequest.type_check(self, [str, unicode]),
                          "machine_type": CheckRequest.type_check(self, [str, unicode]),
                          "usable": CheckRequest.type_check(self, bool)}
        self.required_keys = ["name", "tags", "project", "zone", "in_use"]

    def check_request_create(self, request_dict, required_keys=None, key_types=None):
        return CheckRequest.check_request_create(self, request_dict, required_keys=self.required_keys, key_types=self.key_types)

    def check_request_update(self, request_dict, immutable_keys=None, key_types=None):
        return CheckRequest.check_request_update(self, request_dict, key_types=self.key_types)


def generate_request_checker(backend):
    if backend == 'gce':
        return CheckRequestGcloud
    else:
        return CheckRequest
