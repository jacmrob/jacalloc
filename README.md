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

#### OAuth
If running with a gcloud backend you will need to set up Oauth to validate endpoints.
Create an oauth credential in your google project.  You'll then need to edit `app/templates/flasgger/index.html`: 
```
window.swaggerUi = new SwaggerUi({
       url: url,
       validatorUrl: null,
       dom_id: "swagger-ui-container",
       oauth2RedirectUrl: 'http://your-host-path/flasgger_static/o2c.html', // if running locally, use 'http://localhost:5000/flasgger_static/o2c.html'
       supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
       onComplete: function(swaggerApi, swaggerUi){
           if(typeof initOAuth == "function") {
               initOAuth({
                   clientId: "your-client-id-if-required",
                   clientSecret: "your-client-secret-if-required",
                   realm: "your-project-name",
                   appName: "your-app-name",
                   scopeSeparator: " ",
                   additionalQueryStringParams: {}
               });
           }
```

Enter a redirect URI (which will need to be added to the authorized redirect URIs on your credential), 
the client ID of your credential as `clientId`, and the google project it exists in as `realm`. 
