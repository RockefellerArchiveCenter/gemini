# gemini
A microservice to store AIPs and DIPs in Fedora.

gemini is part of [Project Electron](https://github.com/RockefellerArchiveCenter/project_electron), an initiative to build sustainable, open and user-centered infrastructure for the archival management of digital records at the [Rockefeller Archive Center](http://rockarch.org/).

[![Build Status](https://travis-ci.org/RockefellerArchiveCenter/gemini.svg?branch=base)](https://travis-ci.org/RockefellerArchiveCenter/gemini)
![GitHub (pre-)release](https://img.shields.io/github/release/RockefellerArchiveCenter/gemini/all.svg)

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

gemini has five services, all of which are exposed via HTTP endpoints (see [Routes](#routes) section below):

* Create Packages
  * Handles data from Archivematica's post-store callback and creates database
    objects representing packages to be downloaded.
* Add Data to packages
  * Adds data from the Archivematica API to the packages
* Download Packages
  * Downloads packages from the Archivematica Storage Service.
* Parse METS
  * Parses Archivematica METS file to extract additional metadata.
* Store Packages
  * Storing the package in Fedora, along with minimal metadata.
* Deliver Data - sends package data to another service.
  * Delivering a POST request to a configurable URL. This request has a payload containing the URI of the stored package in Fedora, the package type ("aip" or "dip") and the value of the `Internal-Sender-Identifier` field from the package's `bag-info.txt` file.
* Request Cleanup - send a request to another service to clean up after a package has been processed.

### Routes

| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|GET|/packages| |200|Returns a list of packages|
|GET|/packages/{id}| |200|Returns data about an individual package|
|POST|/download||200|Runs the download routine|
|POST|/store||200|Runs the store routine|
|POST|/deliver||200|Delivers package data to configured URL|
|POST|/request-cleanup||200|Notifies another service that processing is complete|
|GET|/status||200|Return the status of the microservice|
|GET|/schema.json||200|Returns the OpenAPI schema for this application|


## Archivematica Configuration

gemini relies on the proper configuration of Archivematica Storage Service [post-store callbacks](https://www.archivematica.org/en/docs/storage-service-0.16/administrators/#service-callbacks). Two service callbacks, one each for `Post-store AIP` and `Post-store DIP` events, need to be set up as follows:

- Event: either `Post-store AIP` or `Post-store DIP`
- URI: http://zodiac.dev.rockarch.org/api/create-packages/ (This is the configured value of the CreatePackage service's `external_uri` field, prepended by `api/`, and using the correct host name for production or dev).
- Method: POST
- Headers (key/value): key: Content-Type, value: application/json
- Body: {"identifier": "<package_uuid>"}
- Expected status: 200
- Enabled: make sure this is checked

Unfortunately, Archivematica currently does not have a way of testing a service callback, so in order to make sure your newly configured callback is working it is necessary to process a transfer through the pipeline.

### Troubleshooting tips
If the callback is not triggered as expected, you can try a couple of things to troubleshoot:
- Look at the request logs in Zodiac to see if any useful information is provided.
- Make sure that Archivematica can reach Zodiac by sending a cURL request to the configured URL.
- Try mocking the body data required in a cURL request to make sure that Archivematica is sending what you expect.


## Development

This repository contains a configuration file for git [pre-commit](https://pre-commit.com/) hooks which help ensure that code is linted before it is checked into version control. It is strongly recommended that you install these hooks locally by installing pre-commit and running `pre-commit install`.

## License

This code is released under an [MIT License](LICENSE).
