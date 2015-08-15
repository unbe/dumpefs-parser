dumpefs parser
==============

### A parser for QNX dumpefs output that writes the actual files

This is entirely stupid. I could not get the QNX VM to mount my EFS files, so I quickly hacked this up.

Usage:

    dumpefs -t file.efs | python efsasm.py
    ls out

