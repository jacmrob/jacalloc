# jacalloc

Lightweight python app for allocating resources

## Running in docker

```
docker-compose up
```

Can templatize compose and pass in custom db user/pass.

## HTTP API

### GET /resources

Lists all resources

```
curl -X GET http://localhost:5000/resources
curl -X GET http://localhost:5000/resources?in_use=<bool>
```
Returns a list of resources and `200 OK` if successful.

### POST /resources

Creates a new resource

```
curl -X POST -d @record.json http://localhost:5000/resources --header "Content-Type: application/json"
```

Where `record.json` contains
```
{
  "name": "resourceName",
  "ip": "resourceIp",
  "in_use": true || false
}
```

`name` must be unique.  Returns `200 OK` if successful, `409 Conflict` if resource already exists.


### GET /resources/:name

Fetches the resource with `name`
```
curl -X GET http://localhost:5000/resources/<name>
```

Returns the ressource and `200 OK` if successful.

### POST /resources/:name

Modifies a resource.
```
curl -X POST -d @record.json http://localhost:5000/resources/<name> --header "Content-Type: application/json"
```

Returns `200 OK` if successful, `404 Not Found` if resource is not found.

### DELETE /resources/:name
Deletes a resource
```
curl -X DELETE http://localhost:5000/resources/<name>
```
Returns `201 No Content` if successful.

### POST /resources/allocate

Selects a random resource from the set of unused resources and allocates it to `in_use=True`
```
curl -X POST http://localhost:5000/resources/allocate --header "Content-Type: application/json"
```

Returns the resource and `200 OK` if successful.