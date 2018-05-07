# jacalloc

Lightweight python app for allocating resources

## Running in docker

#### Standard
```
docker-compose -f docker-compose.yml up
```

#### Custom gcloud backend

- For each gcloud project `my-project`,
    - create a file `my-project.json` with a service account with Project:Editor permissions
    - create a file `my-project.env` of the format:
    ```dotenv
    PROJECT=my-project
    ZONE=us-central1-a
    SVC_ACCT_PATH=/app/my-project.json
    ```
- Add these files as volumes to the `app` container in `docker-compose-gce.yml`:
    ```yaml
    volumes:
      - ./my-project.json:/app/my-project.json:ro
      - ./my-project.env:/app/my-project.env:ro
    ```
- Run the compose: 
    ```
    docker-compose -f docker-compose-gce.yml up
    ```

## HTTP API

Interactive API documentation is run through [Flasgger](https://github.com/rochacbruno/flasgger).
```
http://localhost:5000/apidocs/index.html
```
