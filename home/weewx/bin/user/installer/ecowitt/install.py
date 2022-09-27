
# installer for the ecowitt skin extension

from setup import ExtensionInstaller

def loader():
    return MySkinInstaller()

class MySkinInstaller(ExtensionInstaller):
    def __init__(self):
        super(MySkinInstaller, self).__init__(
            version="0.5",
            name='ecowitt',
            description='ecowitt minimalist custom skin',
            author="Vince Skahan",
            author_email="vinceskahan@gmail.com",
            config={
                'StdReport': {
                    'ecowitt': {
                        'skin': 'ecowitt',
                        'HTML_ROOT': 'ecowitt'
                        }
                },
                'GW1000': {
                    'ip_address': '192.168.2.20',
                    'port': 45000,
                    'poll_interval': 20,
                    'field_map_extensions': {
                        'outTempBatteryStatus': 'wh26_batt',
                        'batteryStatus1': 'wh31_ch1__batt',
                        'batteryStatus2': 'wh31_ch2__batt',
                        'batteryStatus3': 'wh31_ch3__batt',
                        'batteryStatus4': 'wh31_ch4__batt',
                        'batteryStatus5': 'wh31_ch5__batt',
                        'batteryStatus8': 'wh51_ch1__batt',
                    }
                }
            },
            files=[
                 ('skins/ecowitt',
                    [
                        'skins/ecowitt/index.html.tmpl',
                        'skins/ecowitt/mystyle.css',
                        'skins/ecowitt/skin.conf'
                    ],
                 ),
            ]
        )
