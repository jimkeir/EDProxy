# Elite: Dangerous Netlog Proxy Server #

Replicates the netLog entries (currently System line only) out to any registered listeners via TCP so that an application may run on other platforms. The proxy server will automatically update the E:D configuration to turn on verbose logging.

# Installation #
## Prerequisites for Running Source##
* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [wxPython](http://www.wxpython.org/download.php)
* [psutil](https://github.com/giampaolo/psutil)

## Download ##
Windows: [32-bit](https://bitbucket.org/westokyo/edproxy/downloads/edproxy-1.0.0.zip)

Note: MacOSX should be possible. Someone with a Mac will need to run pyinstaller on the source to generate a binary package.

# Design #
**edproxy** is currently three main components: ED Discovery, ED Netlog Parser, and ED Network. ED Discovery is a new application discovery tool so that applications may find **edproxy** dynamically. ED Netlog Parser is the main component that parses the Elite: Dangerous netLog into event-able messages. ED Network takes in messages and sends out JSON events to all registered listeners.

### ED Discovery ###
The discovery mechanism utilizes UDP multicasting to listen (port 45551), and transmit, messages so that other applications may find a *service*. The *service* should broadcast on startup an **Announce** message. The *announce* will tell any application that is looking for services what application the announcer is broadcasting for, and the IP address (IPv4) and port pair the service is listening on.

Any application that wishes to discover a *service* may broadcast a **Query** command. The *query* may include an option service name. (Ex. *edproxy*) Any service that receives a query with no specified name, or a specified name that matches the service, must immediately send out an **Announce** message.

### ED Netlog Parser ###
The netlog parser reads in the Elite: Dangerous log file, breaks down each line, and events out the messages to any listeners. There are two ways the log file are read: 1) a single instance will open the log file and event out only the current entries being processed, and 2) All entries from a given date will be processed and sent out then wait for new incoming messages from the single instance. This allows for only one file descriptor to be open for the current up-to-date log, but still allow other clients to retrieve historical data.

Currently the only log file line being fully parsed is the System tag lines. These lines contain the system name, number of bodies, ship position in the system, and ship status. Other lines may be supported in the future.

### ED Network ###
*edproxy* will listen on port 45550 for TCP connections from client applications. Once a client connects an initial **Init** command will be sent to *edproxy*. The *init* command will tell *edproxy* how far back in time to ready the log file and will register the client application for which log lines it wishes to receive. From that point forward only events will be sent to the client applications. Each event, and command, is a JSON formatted packet. A single connection may not, currently, be initialized more than once.

# API #
## Discovery API ##
### Announce ###
```
{
    "type": "Announce"
    "name": "Service Name"
    "ipv4": "IP Address"
    "port": Port number
}
```

Example:
``` json
{
    "type": "Announce"
    "name": "edproxy"
    "ipv4": "192.168.1.100"
    "port": 45551
}
```
### Query ###
```
{
    "type": "Query"
    "name": "Service Name" (optional)
}
```

Example:
``` json
{
    "type": "Query"
    "name": "edproxy"
}
```

## Network Commands and Events ##
### Init Command ###
```
{
   "Type": "Init"
   "StartTime": "all" | "now" | "yyyy-mm-ddTHH:MM:SS" (local time)
   "Register": [ "System" ]
}
```

Example:
``` json
{
   "Type": "Init"
   "StartTime": "2015-06-29T13:25:21"
   "Register": [ "System" ]
}
```

### System Event ###
```
{
    "Type": "System"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time)
    "System": "System name"
    "Bodies": Number of Bodies known in System
    "Position": (x, y, z) Coordinates of ship location in system
    "Status": Ship status [ "unknown" | "cruising" ]
}
```

Example:
``` json
{
    "Type": "System"
    "Date": "2015-06-29T13:01:21"
    "System": "Sol"
    "Bodies": 7
    "Position": [ -1234.56, 1234.56, 8765.87 ]
    "Status": "cruising"
}
```

## Contact ###

* Author [Weston Boyd](mailto://gen.fussypants@gmail.com)