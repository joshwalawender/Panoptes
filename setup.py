from setuptools import setup, find_packages
setup(
    name = "PanoptesScripts",
    version = "1.1",
    author='Josh Walawender',
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'MeasureImage = MeasureImage:main',
            'MeasureNight = MeasureNight:main',
            'MonitorImages = Monitor:main',
            'CleanupIQMon = CleanupIQMon:main',
        ]
    }
)
