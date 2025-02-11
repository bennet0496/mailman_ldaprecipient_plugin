from contextlib import suppress

import ldap3
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.member import MemberRole
from mailman.interfaces.rules import IRule
from mailman.interfaces.usermanager import IUserManager
from public import public
from zope.component import getUtility
from zope.interface import implementer
from mailman.rules.moderation import MemberModeration, NonmemberModeration


@public
@implementer(IRule)
class LdapMemberModeration:
    """The member moderation rule."""

    name = 'member-moderation-ldap'
    description = _('Match messages sent by moderated LDAP members.')
    record = True

    def __init__(self):
        self._plugin = config.plugins['mailman_ldaprecipient_plugin']

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        tls = None
        if self._plugin.ldap_tls_cert is not None:
            tls = ldap3.Tls(ca_certs_file=self._plugin.ldap_tls_cert)
        srv = ldap3.Server(self._plugin.ldap_uri, int(self._plugin.ldap_port or 389), tls=tls)
        conn = ldap3.Connection(srv, user=self._plugin.ldap_bind_dn, password=self._plugin.ldap_bind_pass)
        if self._plugin.ldap_tls_cert is not None:
            conn.start_tls()

        conn.bind()

        # The MemberModeration rule misses unconditionally if any of the
        # senders are banned.
        ban_manager = IBanManager(mlist)
        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False

        for sender in msg.senders:
            conn.search(self._plugin.ldap_user_base, "(mail={})".format(sender), attributes=["uid", "mail", "cn"])
            if len(conn.entries) > 0:
                break
        else:
            return self._plugin.original_member_moderation_rule.check(mlist, msg, msgdata)

        action = mlist.default_member_action
        if action is Action.defer:
            # The regular moderation rules apply.
            return False
        elif action is not None:
            # We must stringify the moderation action so that it can be
            # stored in the pending request table.
            msgdata['member_moderation_action'] = action.name
            msgdata['moderation_sender'] = sender
            return True
        # The sender is not a member so this rule does not match.
        return self._plugin.original_member_moderation_rule.check(mlist, msg, msgdata)

@public
@implementer(IRule)
class LdapNonMemberModeration:
    """The member moderation rule."""

    name = 'nonmember-moderation-ldap'
    description = _('Match messages sent by nonmembers.')
    record = True

    def __init__(self):
        self._plugin = config.plugins['mailman_ldaprecipient_plugin']

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""

        tls = None
        if self._plugin.ldap_tls_cert is not None:
            tls = ldap3.Tls(ca_certs_file=self._plugin.ldap_tls_cert)
        srv = ldap3.Server(self._plugin.ldap_uri, int(self._plugin.ldap_port or 389), tls=tls)
        conn = ldap3.Connection(srv, user=self._plugin.ldap_bind_dn, password=self._plugin.ldap_bind_pass)
        if self._plugin.ldap_tls_cert is not None:
            conn.start_tls()

        conn.bind()

        ban_manager = IBanManager(mlist)

        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False
        if len(msg.senders) == 0:
            return self._plugin.original_nonmember_moderation_rule.check(mlist, msg, msgdata)
        # Every sender email must be a member or nonmember directly.  If it is
        # neither, make the email a nonmembers.
        for sender in msg.senders:
            conn.search(self._plugin.ldap_user_base, "(mail={})".format(sender), attributes=["uid", "mail", "cn"])
            if len(conn.entries) == 0:
                return self._plugin.original_nonmember_moderation_rule.check(mlist, msg, msgdata)

        return False