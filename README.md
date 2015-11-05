# Elite: Dangerous Netlog Proxy Server #

Replicates the netLog entries (currently System line only) out to any registered listeners via TCP so that an application may run on other platforms. The proxy server will automatically update the E:D configuration to turn on verbose logging.

# Installation #
## Prerequisites for Running Source##
* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [wxPython](http://www.wxpython.org/download.php)
* [psutil](https://github.com/giampaolo/psutil)
* [watchdog](http://pythonhosted.org/watchdog/)
* [Pillow](https://python-pillow.github.io/)

## Install using PIP

```
#!bash

$ pip install psutil
```

```
#!bash

$ pip install watchdog
```

```
#!bash

$ pip install Pillow
```

## Download ##
Windows: [32-bit](https://bitbucket.org/westokyo/edproxy/downloads/LATEST-win32)
Mac OSx: [DMG File](https://bitbucket.org/westokyo/edproxy/downloads/LATEST-macosx)

Note: MacOSX should be possible. Someone with a Mac will need to run pyinstaller, or py2app, on the source to generate a binary package.

# Design #
## Feature Modules ##
* Service Discovery
* Elite: Dangerous Netlog Parser
* Image Acquisition
* Network Connection Management

### Service Discovery ###
The discovery mechanism utilizes UDP multicasting to listen (port 45551), and transmit, messages so that other applications may find a *service*. The *service* should broadcast on startup an **Announce** message. The *announce* will tell any application that is looking for services what application the announcer is broadcasting for, and the IP address (IPv4) and port pair the service is listening on.

Any application that wishes to discover a *service* may broadcast a **Query** command. The *query* may include an option service name. (Ex. *edproxy*) Any service that receives a query with no specified name, or a specified name that matches the service, must immediately send out an **Announce** message.

### Elite: Dangerous Netlog Parser ###
The netlog parser reads in the Elite: Dangerous log file, breaks down each line, and events out the messages to any listeners. There are two ways the log file are read: 1) a single instance will open the log file and event out only the current entries being processed, and 2) All entries from a given date will be processed and sent out then wait for new incoming messages from the single instance. This allows for only one file descriptor to be open for the current up-to-date log, but still allow other clients to retrieve historical data.

Currently the only log file line being fully parsed is the System tag lines. These lines contain the system name, number of bodies, ship position in the system, and ship status. Other lines may be supported in the future.

### Image Acquisition ###
*edproxy* is capable of monitoring a directory for new image files and sending those files out as events. The image acquisition service monitors for new ".bmp" files, optionally changes the name to a human readable format, optionally converts to either ".png" or ".jpg", and finally optionally deletes the original. All options may be configured from within the *Preferences* dialog.

The image acquisition service runs its own private web server internally so that *edproxy* is not sending out entire image files unless requested. Thus the *Image* event will only contain a URL to said image.

### Network Connection Management ###
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
   "Heartbeat": Integer (optional default: -1. Represents the number of seconds between heartbeats)
}
```

Example:
``` json
{
   "Type": "Init"
   "StartTime": "2015-06-29T13:25:21"
   "Register": [ "System" ]
   "Heartbeat": 30
}
```

### Heartbeat (Ping) Event ###
```
{
   "Type": "Heartbeat"
   "Date": "yyyy-mm-ddTHH:MM:SS" (local time)
}
```

Example:
``` json
{
   "Type": "Heartbeat"
   "Date": "2015-06-29T13:01:21"
}
```

### Pong (Heartbeat Acknowledge) Event ###
```
{
   "Type": "Pong"
   "Date": "yyyy-mm-ddTHH:MM:SS" (local time)
}
```

Example:
``` json
{
   "Type": "Pong"
   "Date": "2015-06-29T13:01:21"
}
```

### System Event ###
```
{
    "Type": "System"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time)
    "System": "System name"
    "Bodies": Number of Bodies known in System
    "Position": [x, y, z] Coordinates of ship location in system
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

### Image Event ###
```
{
    "Type": "Image"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS" (UTC time)
    "ImageUrl": "URL"
}
```

Example:
``` json
{
    "Type": "Image"
    "Date": "2015-06-29T13:01:21"
    "System": "http://192.168.1.128:8097/Sol_2015-06-29_13-01-21.png"
}
```

### Import Event ###
```
{
    "Type": "Import"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS" (UTC time)
    "System": "System name"
    "Position": [x, y, z] Coordinates for the System
    "MainStar": "Stellar Type"
    "StellarBodies": Number of Stellar Bodies known in System
    "StellarTypes": [ "Array of Stellar Types" ]
    "PlanetaryBodies": Number of Planetary Bodies known in System
    "PlanetTypes": [ "Array of Planet Types" ]
    "Notes": "Notes for the system"
    "RefDistances": [ { "System": "System name", "Distance": 123.45 } ]
}
```

Example:
``` json
{
    "Type": "Import"
    "Date": "2015-06-29T13:01:21"
    "System": "Sol"
    "Position": [ 0.00, 0.00, 0.00 ]
    "MainStar": "Put in value"
    "StellarBodies": 1
    "StellarTypes": [ "Put in value" ]
    "PlanetaryBodies": 6
    "PlanetTypes": [ "Earth-Like" ]
    "Notes": "This is home!"
    "RefDistances": [ { "System": "Put in value", "Distance": 123.45 } ]
}
```

# Contact #

* Author [Weston Boyd](mailto://fussyware@gmail.com)