# Elite: Dangerous Netlog Proxy Server #

Replicates the netLog entries (currently System line only) out to any registered listeners via TCP so that an application may run on other platforms. The proxy server will automatically update the E:D configuration to turn on verbose logging.

# Installation #
## Prerequisites ##
* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [wxPython](http://www.wxpython.org/download.php)
* [psutil](https://github.com/giampaolo/psutil)

An all-in-one package is currently being worked on.

# Design #
*Work In Progress*

**edproxy** is currently three main components: ED Discovery, ED Netlog Parser, and ED Network. ED Discovery is a new application discovery tool so that applications may find **edproxy** dynamically. ED Netlog Parser is the main component that parses the Elite: Dangerous netLog into event-able messages. ED Network takes in messages and sends out JSON events to all registered listeners.

### ED Discovery ###
The discovery mechanism utilizes UDP multicasting to listen, and transmit, messages so that other applications may find a *service*. The *service* should broadcast on startup an **Announce** message. The *announce* will tell any application that is looking for services what application the announcer is broadcasting for, and the IP address (IPv4) and port pair the service is listening on.

Any application that wishes to discover a *service* may broadcast a **Query** command. The *query* may include an option service name. (Ex. *edproxy*) Any service that receives a query with no specified name, or a specified name that matches the service, must immediately send out an **Announce** message.

## ED Netlog Parser ##


# API #
*Work In Progress*

## Contact ###

* Author [Weston Boyd](mailto://Weston.Boyd@fussyware.com)