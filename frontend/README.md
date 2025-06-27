# Frontend

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 16.2.7.

## Install and Run

### Local deployment

1. Install node and npm.
   Ubuntu: `sudo apt install nodejs`
   MacOS: `brew install node`

2. Install node modules dependencies running `npm install` in this directory.

3. Install Angular `npm install -g @angular/cli`

4. Run the local development web server `npm start`

4b. (alternative to `npm start`) Serve via `ng`
   Once angular and npm packages have been installed, manually copy the configuration file and run the server
   ```
   cp src/assets/configs/config.local.json src/assets/configs/config.json
   ng serve
   ```
   Following this step, a `BACKEND_IP` different from `localhost` can be supported.

5. Open the browser to `http://{BACKEND_IP}:4200/`

> Please note that, when running on a cloud environment, the host may need to be exposed in order to be accessible
> `ng serve --host 0.0.0.0`

### Deployment via docker
1. Build the frontend for docker `ng build --configuration docker`
2. Run backend and frontend together (from the root) `docker compose up`

## Development notes

### Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`.
The application will automatically reload if any of the source files is changed.


### Code scaffolding

Run `ng generate component component-name` to generate a new component.
You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

### Build

Run `ng build` to build the project.
The build artifacts will be stored in the `dist/` directory.

### Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

### Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via a platform of your choice.
To use this command, you need to first add a package that implements end-to-end testing capabilities.

### Further notes

To get get help on the Angular CLI use `ng help`, or check the [Angular CLI Overview and Command Reference](https://angular.io/cli) page.
