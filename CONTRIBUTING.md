# Elite: Dangerous Netlog Proxy Server - Developers Guide #

This guide assumes the developer is using _Microsoft Windows_ as the
development platform. There is no requirement for this and developers are
encouraged to add platform-specific instructions to this file.

"$" is used to designate the Prompt throughout this guide for any 
commands which should be typed into a shell, even though a Windows
Batch Shell prompts using the current working directory; for example:
```
C:\Source\EdProxy\>
```

# Editing the Source Code #

Please follow the coding conventions in the source files; specifically,
indentation is via **4 spaces** and not via tabs.

The developers have used a variety of editors, including _emacs_, _Notepad++_,
and _Android Studio_.

# Running the Source Code #

The entry point is _edproxy.py_:

```
$ python edproxy.py
```

## Prerequisites for running the source code ##
* [Python 2.7](https://www.python.org/download/releases/2.7/)
* [wxPython](http://www.wxpython.org/download.php)
* [psutil](https://github.com/giampaolo/psutil)
* [watchdog](http://pythonhosted.org/watchdog/)
* [Pillow](https://python-pillow.github.io/)
* SendKeys
    + [Microsoft Visual C++ Compiler for Python 2.7](https://www.microsoft.com/en-us/download/details.aspx?id=44266)
* ijson
* Tornado

**NB:** To ensure all of the following instructions work, Python must be added
to the PATH environment variable. By default, the following directories must
be added:

```
$ PATH=%PATH%;C:\Python27;C:\Python27\Scripts
```

### Installing the pre-requisites using PIP ###

```
$ python -m pip install psutil watchdog Pillow Sendkeys tornado ijson
```

## Running the tests ##

TODO

# Building the Distribution Packages - Windows #

## Pre-requisites for building the distribution packages ##

* [PyInstaller](http://www.pyinstaller.org/)
* [Inno Setup](http://www.jrsoftware.org/isinfo.php)

### Install using PIP ###

PyInstaller can be installed using PIP; Inno Setup must be installed manually.

```
$ python -m pip install pyinstaller
```

## Creating the binary ##

A helper batch-file is included to create the binary, which takes a while to run.

```
$ win32-pyinstall.bat
```

The output is placed in the 'dist' directory from where it can be run and tested.

## Creating the Installer ##

The configuration file for the installer is "win-innosetup.iss" and is located
in the root directory of the source tree. If the default options are selected
when installing _Inno Setup_, double-clicking on this file starts _Inno Setup_.

Edit the version number (if necessary), then click the "Compile" icon or
use the "Build -> Compile" menu option to generate the installer.

The installer is generated in the "Output" directory. It can be installed
using the "Run" option in _Inno Setup_, or by running it directly.


# Building the Distribution Packages - Mac OsX #

TODO
