# This is what your ‘setup.py’ file should look like.

from setuptools import setup, find_packages

setup(
    name="mailman_ldaprecipient_plugin", #Name
    # version="0.1.0", #Version
    use_scm_version=True,
    # setup_requires=["setuptools_scm"],
    description='LDAP Recipients for Mailman3 Mailinglists',
    author='Bennet Becker',
    author_email='bbecker@pks.mpg.de',
    url='https://github.com/bennet0496/mailman_ldaprecipient_plugin',
    packages = find_packages('.'),
)