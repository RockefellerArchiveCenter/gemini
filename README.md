# gemini
A microservice to store AIPs and DIPs in Fedora.

gemini is part of [Project Electron](https://github.com/RockefellerArchiveCenter/project_electron), an initiative to build sustainable, open and user-centered infrastructure for the archival management of digital records at the [Rockefeller Archive Center](http://rockarch.org/).

[![Build Status](https://travis-ci.org/RockefellerArchiveCenter/gemini.svg?branch=master)](https://travis-ci.org/RockefellerArchiveCenter/gemini)

## Setup

Install [git](https://git-scm.com/) and clone the repository

    $ git clone git@github.com:RockefellerArchiveCenter/gemini.git

Install [Docker](https://store.docker.com/search?type=edition&offering=community) and run docker-compose from the root directory

    $ cd gemini
    $ docker-compose up

Once the application starts successfully, you should be able to access the application in your browser at `http://localhost:8006`

When you're done, shut down docker-compose

    $ docker-compose down

Or, if you want to remove all data

    $ docker-compose down -v


### Configuration

You will need to edit configuration values in `gemini/config.py` to point to your instances of Archivematica and Fedora.


## Services

gemini has three services, all of which are exposed via HTTP endpoints (see [Routes](#routes) section below):

* Download Packages
  * Polling the Archivematica Storage Service for packages.
  * Determining if the package has already been stored by checking whether or not it exists as an object in gemini's database. If the package has already been processed, gemini skips it and goes to the next one.
  * Downloading the package from the Archivematica Storage Service.
* Store Packages
  * Storing the package in Fedora, along with minimal metadata.
  * Creating a package object in gemini's database.
  * Delivering a POST request to a configurable URL. This request has a payload containing the URI of the stored package in Fedora, the package type ("aip" or "dip") and the value of the `Internal-Sender-Identifier` field from the package's `bag-info.txt` file.
* Request Cleanup - send a request to another service to clean up after a package has been processed.

![File storage diagram](gemini-services.png)


### Routes

| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|GET|/packages| |200|Returns a list of packages|
|GET|/packages/{id}| |200|Returns data about an individual package|
|POST|/download||200|Runs the download routine|
|POST|/store||200|Runs the store routine|
|POST|/request-cleanup||200|Notifies another service that processing is complete|
|GET|/status||200|Return the status of the microservice|
|GET|/schema.json||200|Returns the OpenAPI schema for this application|


## Logging

gemini uses `structlog` to output structured JSON logs. Logging can be configured in `gemini/settings.py`.


## License

This code is released under an [MIT License](LICENSE).
