# Elite: Dangerous Netlog Proxy Server #

Replicates the netLog entries (currently System line only) out to any registered listeners via TCP so that an application may run on other platforms. The proxy server will automatically update the E:D configuration to turn on verbose logging.

# Installation #
## Binary Download ##
Windows: [32-bit](https://bitbucket.org/westokyo/edproxy/downloads/LATEST-win32)

Mac OSx: [DMG File](https://bitbucket.org/westokyo/edproxy/downloads/LATEST-macosx)

## Prerequisites for Running Source##
* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [wxPython](http://www.wxpython.org/download.php)
* [psutil](https://github.com/giampaolo/psutil)
* [watchdog](http://pythonhosted.org/watchdog/)
* [Pillow](https://python-pillow.github.io/)
* SendKeys
** [Microsoft Visual C++ Compiler for Python 2.7](https://www.microsoft.com/en-us/download/details.aspx?id=44266)
* ijson
* Tornado

## Install using PIP

```
#!bash

$ python -m pip install psutil watchdog Pillow Sendkeys tornado ijson
```

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
   "DateUtc": "yyyy-mm-ddTHH:MM:SS"
   "StartTime": "all" | "now" | "yyyy-mm-ddTHH:MM:SS" (local time)
   "Register": [ "System" ]
   "Heartbeat": Integer (optional default: -1. Represents the number of seconds between heartbeats)
}
```

Example:
``` json
{
   "Type": "Init"
   "DateUtc": "2015-06-29T19:25:21"
   "StartTime": "2015-06-29T13:25:21"
   "Register": [ "System" ]
   "Heartbeat": 30
}
```

### Heartbeat (Ping) Event ###
```
{
   "Type": "Heartbeat"
   "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
   "DateUtc": "yyyy-mm-ddTHH:MM:SS"
}
```

Example:
``` json
{
   "Type": "Heartbeat"
   "DateUtc": "2015-06-29T19:25:21"
}
```

### Pong (Heartbeat Acknowledge) Event ###
```
{
   "Type": "Pong"
   "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
   "DateUtc": "yyyy-mm-ddTHH:MM:SS"
}
```

Example:
``` json
{
   "Type": "Pong"
   "DateUtc": "2015-06-29T19:25:21"
}
```

### System Event ###
```
{
    "Type": "System"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
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
    "DateUtc": "2015-06-29T19:25:21"
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
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
    "ImageUrl": "URL"
}
```

Example:
``` json
{
    "Type": "Image"
    "DateUtc": "2015-06-29T19:25:21"
    "System": "http://192.168.1.128:8097/Sol_2015-06-29_13-01-21.png"
}
```

### Send Keys Event (Windows Only) ###
```
{
    "Type": "SendKeys"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
    "Keys": "Keys to Event"
}
```

Example:
``` json
{
    "Type": "SendKeys"
    "DateUtc": "2015-06-29T19:25:21"
    "Keys": "Sol"
}
```

### Star Map Updated Event ###
```
{
    "Type": "StarMapUpdated"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
}
```

Example:
``` json
{
    "Type": "StarMapUpdated"
    "DateUtc": "2015-06-29T19:25:21"
}
```

### Get Distances Event ###
```
{
    "Type": "GetDistances"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
    "Distances": [ { "sys1": "System Name", "sys2": "System Name" } ]
}
```

Example:
``` json
{
    "Type": "GetDistances"
    "DateUtc": "2015-06-29T19:25:21"
    "Distances": [ { "sys1": "Sol", "sys2: "Kured" }, { "sys1": "Kured", "sys2": "Marowalan" } ]
}
```


### Get Distances Result Event ###
```
{
    "Type": "GetDistancesResult"
    "Date": "yyyy-mm-ddTHH:MM:SS" (local time) (Deprecated)
    "DateUtc": "yyyy-mm-ddTHH:MM:SS"
    "Distances": [ { "sys1": "System Name", "sys2": "System Name", "dist": 123.45 } ]
}
```

Example:
``` json
{
    "Type": "GetDistancesResult"
    "DateUtc": "2015-06-29T19:25:21"
    "Distances": [ { "sys1": "Sol", "sys2: "Kured", "dist": 123.45 }, { "sys1": "Kured", "sys2": "Marowalan", "dist": 8.12 } ]
}
```

# Contact #

* Author [Weston Boyd](mailto://fussyware@gmail.com)