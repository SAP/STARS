# Docker

To run the agent application (frontend and backend) using Docker, just run
```
docker compose up
```


## Docker Troubleshooting


### Database issues
`sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file`

Try to set the DB_PATH in `.env` to a different location, possibly under `/app` path.


### AI Core connection issues
`AIAPIAuthenticatorAuthorizationException: Could not retrieve Authorization token: {"error":"invalid_client","error_description":"Bad credentials"}`

This error indicates that the AI Core is not able to authenticate with the
provided credentials. Ensure that all the `AICORE_` env variables are set in
`.env` and try to set the values of `AICORE_CLIENT_ID` and
`AICORE_CLIENT_SECRET` withing quotes (they may contain special characters).

### No communication between frontend and backend

`failed to solve: failed to compute cache key: failed to calculate checksum of ref ldjsx0lwjdmaj80rvuzvqjszw::hnkg508y95ilcd8l50qt5886h: "/dist/stars": not found`

If the frontend is not able to communicate with the backend (and you can see
the red error message in the browser `No connection to Agent. Make sure the
agent is reachable and refresh this page.`), first try to refresh the page,
then, if the error persists, follow the steps in `/frontend` to rebuild the
frontend and re-launch the Docker containers.

Alternatively, review the configuration and the chosen backend endpoint (and
consider a local test run using `localhost`).
