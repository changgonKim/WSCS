# WSCS

![Versions](https://img.shields.io/badge/python->3.8-blue)

WSCS camera system

## Quick Start

### Prerequisite

Make the directory to run and develop the code first.
```
$ mkdir WSCS
$ cd WSCS
```

Clone the WSCS code by git clone inside the directory.
```
$ git clone https://github.com/changgonKim/WSCS.git
```

Install [poetry](https://python-poetry.org/) by using PyPI.
```
$ pip install poetry
```

Run poetry install to install the dependencies

```
$ poetry install
```

Run the GUI code 

```
$ python WSCS_GUI.py
```

## ERROR HANDLING

The error handling will written here.

### 1. The EDSDK error

For EDSDK error, you have to download the edsds.dll from [here](https://www.dll4free.com/edsdk.dll.html)

Click download button at there.

And add it in your Following window directory:

C:\Windows\System32 for 32 bit
and
C:\Windows\SysWOW64 for 64 bit

Then try to connect the Camera in the GUI again.

### 2. ImportError: Cannot find LibRaw on your system!

In this case, follow this instruction [here](http://w3devlabs.net/wp/?p=32534). This is in Korean, so if you want English description, it is [here](https://github.com/mateusz-michalik/cr2-to-jpg/issues/1)

Please make a issue if there are more other issues on using this.