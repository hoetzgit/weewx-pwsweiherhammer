# installer for Meteo-services.com
# Copyright 2016-2021 Frank Bandle (based on scripts M. Wall)

from setup import ExtensionInstaller


def loader():
    return MeteoservicesInstaller()


class MeteoservicesInstaller(ExtensionInstaller):
    def __init__(self):
        super(MeteoservicesInstaller, self).__init__(
            version="3.2",
            name='Meteoservices',
            description='Upload weather data Meteo-services.com HiQ-Network',
            author="Frank Bandle",
            author_email="support@meteo-services.com",
            restful_services='user.meteoservices.Meteoservices',
            config={
                'StdRESTful': {
                    'Meteoservices': {
                        'stationid': 'INSERT_STATIONID_HERE',
                        'password': 'INSERT_PASSWORD_HERE'}}},
            files=[('bin/user', ['bin/user/meteoservices.py'])]
        )
