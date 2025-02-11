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

    # Documentation for mlist can be found here: https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/rest/docs/listconf.html
    def process(self, mlist, msg, msgdata):
        """Add the LDAP Recipients to the email."""
        ldaphost = None
        ldapport = None
        ldapbind = None
        ldappass = None
        ldapgbase = None
        ldapubase = None
        ldaptls = None
        ldapmatchattr = None
        for name, section in config.plugin_configs:
            # print(name, section)
            if name == "mailman_ldaprecipient_plugin":
                cf = configparser.ConfigParser()
                cf.read(section.configuration)

                ldaphost = "ldap_uri" in cf["ldap"] and cf["ldap"]["ldap_uri"] or None
                ldapport = "ldap_port" in cf["ldap"] and cf["ldap"]["ldap_port"] or None
                ldapbind = "ldap_bind_dn" in cf["ldap"] and cf["ldap"]["ldap_bind_dn"] or None
                ldappass = "ldap_bind_pass" in cf["ldap"] and cf["ldap"]["ldap_bind_pass"] or None
                ldapgbase = "ldap_group_base" in cf["ldap"] and cf["ldap"]["ldap_group_base"] or None
                ldapubase = "ldap_user_base" in cf["ldap"] and cf["ldap"]["ldap_user_base"] or None
                ldaptls = "ldap_tls_cert" in cf["ldap"] and cf["ldap"]["ldap_tls_cert"] or None
                ldapmatchattr = "ldap_match_listid_attr" in cf["ldap"] and cf["ldap"]["ldap_match_listid_attr"] or "listId"
                break
        if ldaphost is None:
            raise Exception("No LDAP host configured")

        tls = None
        if ldaptls is not None:
            tls = ldap3.Tls(ca_certs_file=ldaptls)
        srv = ldap3.Server(ldaphost, int(ldapport or 389), tls=tls)
        conn = ldap3.Connection(srv, user=ldapbind, password=ldappass)
        if ldaptls is not None:
            conn.start_tls()

        conn.bind()
        conn.search(ldapgbase, "({}={}.{})".format(ldapmatchattr, mlist.list_name, mlist.mail_host),
                    attributes=ldap3.ALL_ATTRIBUTES, get_operational_attributes=False)

        if len(conn.entries) == 0:
            return

        groups = conn.entries
        recipients = []
        for group in groups:
            if "posixGroup" in group["objectClass"] or "memberUid" in group:
                ufilter = ")(uid=".join(group["memberUid"])
                ufilter = "(|(uid={}))".format(ufilter)
                conn.search(ldapubase, ufilter, attributes=["mail"], get_operational_attributes=False)
                for entry in conn.entries:
                    recipients.append(str(entry["mail"]))
            else:
                conn.search(ldapubase, "(memberOf={})".format(group["DN"]), attributes=["mail"], get_operational_attributes=False)
                for entry in conn.entries:
                    recipients.append(str(entry["mail"]))

        msgdata['recipients'] = msgdata['recipients'].union(recipients)