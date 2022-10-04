"""
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

                 Installer for the Cumulative XType Extension

Version: 0.1.0                                          Date: 2 October 2022

Revision History
    2 October 2022      v0.1.0
        -   initial implementation
"""

# python imports
from distutils.version import StrictVersion
from setup import ExtensionInstaller

# WeeWX imports
import weewx


REQUIRED_VERSION = "4.6.0"
XCUM_VERSION = "0.1.0"


def loader():
    return XCumulativeInstaller()


class XCumulativeInstaller(ExtensionInstaller):
    def __init__(self):
        if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_VERSION):
            msg = "%s requires WeeWX %s or greater, found %s" % (''.join(('Cumulative XType ', XCUM_VERSION)),
                                                                 REQUIRED_VERSION,
                                                                 weewx.__version__)
            raise weewx.UnsupportedFeature(msg)
        super(XCumulativeInstaller, self).__init__(
            version=XCUM_VERSION,
            name='XCumulative',
            description='A WeeWX XType to produce cumulative series data with user specified reset times.',
            author="Gary Roderick",
            author_email="gjroderick<@>gmail.com",
            xtype_services=['user.xcumulative.StdCumulativeXType'],
            files=[('bin/user', ['bin/user/xcumulative.py'])]
        )
