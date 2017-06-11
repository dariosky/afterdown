from setuptools import setup, find_packages

setup(
    name='afterdown',
    version='0.9.9',
    packages=find_packages(),
    include_package_data=True,

    url='https://github.com/dariosky/afterdown',
    license='GPL2',
    author='Dario Varotto',
    author_email='dario.varotto@gmail.com',
    description='Automate the organization of your downloads.',

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: System :: Software Distribution',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='deployment webfaction cli letsencrypt certificate',
    install_requires=['dropbox', 'requests', 'pytest',
                      'six', 'future',
                      'guessit', 'subliminal',
                      ],
    entry_points={
        'console_scripts': ['afterdown = afterdown.__main__:main'],
    }

)
