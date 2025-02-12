import configparser

import ldap3
from public import public
from zope.interface import implementer
from mailman.interfaces.handler import IHandler
from mailman.handlers.cook_headers import uheader
from email.utils import formataddr
from mailman.config import config

from mailman_ldaprecipient_plugin.ldap import find_list_group


# from mailman.config.config import load_external


# Use this in the process function: raise DiscardMessage('Message was discarded because ...')
#from mailman.interfaces.pipeline import (
#    DiscardMessage,
#    RejectMessage,
#)

#import logging
#elog = logging.getLogger("mailman.error")
# Use this for logging in functions
#elog.error('My error message')

@public
@implementer(IHandler)
class SenderHeaderHandler:
    """A handler to add the Sender header to each email."""

    # The name of the handler should be unique.
    name = 'mailman-sender-handler'
    description = 'Add the Sender header to emails.'

    # Documentation for mlist can be found here: https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/rest/docs/listconf.html
    def process(self, mlist, msg, msgdata):
        """Add the Sender header to the email."""
        # Do not add already set headers, it would exist twice afterwards
        if not 'Sender' in msg:
            # Add the Sender header using the mailing list post address
            i18ndesc = str(uheader(mlist, mlist.description, 'Sender'))
            msg['Sender'] = formataddr((i18ndesc, mlist.bounces_address))

@public
@implementer(IHandler)
class MailmanHeaderCleanerHandler:
    """A handler to edit the mailman headers for each email."""

    # The name of the handler should be unique.
    name = 'mailman-headers-handler'
    description = 'Edit the mailman header for emails.'

    def process(self, mlist, msg, msgdata):
        """Edit the mailman header for emails."""
        # Remove some headers
        del msg['X-Mailman-Version']
        del msg['X-Mailman-Rule-Misses']
        del msg['X-Mailman-Rule-Hits']

@public
@implementer(IHandler)
class LdapRecipientHandler:
    """A handler to add the LDAP recipients."""

    # The name of the handler should be unique.
    name = 'ldap-recipients'
    description = 'Add List Recipients from LDAP.'

    # Documentation for mlist can be found here: https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/rest/docs/listconf.html
    def process(self, mlist, msg, msgdata):
        """Add the LDAP Recipients to the email."""

        ldap_group = find_list_group(mlist)

        msgdata['recipients'] = msgdata['recipients'].union(ldap_group['member_emails'])