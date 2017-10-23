# campaign-monitor-proxy

A simple web app that serves as a basic HTTP proxy the createsend's API


## Requirements

The only requirements to start the app are django and `createsend` HTTP client


## Running the app

The app comes with its own docker image, which eases deployment and testing.
In order to test it locally, simply run:

    docker pull cpollalis/campaign-poc
    docker run --rm -p 8000:8000 -e API_KEY=YOUR_API_KEY -it campaign-poc

This will start the docker container and make the app available at port 8000.
The API key used to authentication to createsend's API can be provided to the
django app as an environmental variable.


### Looking at your mailing lists

In order to have a look at your campaign information visit http://localhost:8000/CLIENTID.
Your ClientID can be obtained from campaignmonitoring.com.


## Developing the app

If you wish to modify the app's source code, while running/testing it, you will
a clone of the git repository. After you have cloned the repo, run:

    docker run --rm -p 8000:8000 -v `pwd`:/campaign -e API_KEY=YOUR_API_KEY -it campaign-poc sh

This will drop you in a shell inside the container and mount your local code.
At this point, you may start django's development server.

See `./manage.py runserver -h` for more.
