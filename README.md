# jacalloc

Lightweight python app for allocating resources

## Running in docker

```
docker-compose up
```

Can templatize compose and pass in custom db user/pass.

## HTTP API

### POST /allocate

Adds a record if one does not exist, or updates an existing record

```
curl -X POST -d @record.json http://localhost:5000/allocate --header "Content-Type: application/json"
```

Where `record.json` contains
```
{
  "name": "resourceName",
  "ip": "resourceIp",
  "in_use": true || false
}
```

`name` and `ip` must be unique.  Returns `200 OK` if successful.

### GET /query

Queries for the status of a resource.  Can query on `name` or `ip`, or without query parameters to return a list of all unallocated resources.
```
curl -X GET http://localhost:5000/query
curl -X GET http://localhost:5000/query?name=<name>
curl -X GET http://localhost:5000/query?ip=<ip>
```

Returns `200 OK` if successful.  If querying on a resource, returns "True" if resource is free or "False" if resource is allocated.  Otherwise, returns list of all unallocated resources.