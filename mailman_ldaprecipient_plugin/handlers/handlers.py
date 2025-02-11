import configparser

import ldap3
from public import public
from zope.interface import implementer
from mailman.interfaces.handler import IHandler
from mailman.handlers.cook_headers import uheader
from email.utils import formataddr
from mailman.config import config
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

    def __init__(self):
        self._plugin = config.plugins['mailman_ldaprecipient_plugin']

    # Documentation for mlist can be found here: https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/rest/docs/listconf.html
    def process(self, mlist, msg, msgdata):
        """Add the LDAP Recipients to the email."""

        tls = None
        if self._plugin.ldap_tls_cert is not None:
            tls = ldap3.Tls(ca_certs_file=self._plugin.ldap_tls_cert)
        srv = ldap3.Server(self._plugin.ldap_uri, int(self._plugin.ldap_port or 389), tls=tls)
        conn = ldap3.Connection(srv, user=self._plugin.ldap_bind_dn, password=self._plugin.ldap_bind_pass)
        if self._plugin.ldap_tls_cert is not None:
            conn.start_tls()

        conn.bind()

        conn.bind()
        conn.search(self._plugin.ldap_group_base, "({}={}.{})".format(self._plugin.ldap_match_listid_attr, mlist.list_name, mlist.mail_host),
                    attributes=ldap3.ALL_ATTRIBUTES, get_operational_attributes=False)

        if len(conn.entries) == 0:
            return

        groups = conn.entries
        recipients = []
        for group in groups:
            if "posixGroup" in group["objectClass"] or "memberUid" in group:
                ufilter = ")(uid=".join(group["memberUid"])
                ufilter = "(|(uid={}))".format(ufilter)
                conn.search(self._plugin.ldap_user_base, ufilter, attributes=["mail"], get_operational_attributes=False)
                for entry in conn.entries:
                    recipients.append(str(entry["mail"]))
            else:
                conn.search(self._plugin.ldap_user_base, "(memberOf={})".format(group["DN"]), attributes=["mail"], get_operational_attributes=False)
                for entry in conn.entries:
                    recipients.append(str(entry["mail"]))

        msgdata['recipients'] = msgdata['recipients'].union(recipients)