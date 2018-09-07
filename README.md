# gemini
A microservice to store AIPs and DIPs in Fedora.

## Setup

Clone the repository

    $ git clone git@github.com:RockefellerArchiveCenter/gemini.git

Install [Docker](https://store.docker.com/search?type=edition&offering=community) (trust me, it makes things a lot easier)

Run docker-compose from the root directory

    $ cd gemini
    $ docker-compose up

Once the application starts successfully, you should be able to access the application in your browser at `http://localhost:8006`

When you're done, shut down docker-compose

    $ docker-compose down


## Usage

![File storage diagram](storer.png)


## License

Gemini is released under an MIT License. See [LICENSE](LICENSE) for details.
