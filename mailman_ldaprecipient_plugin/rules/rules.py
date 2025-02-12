import ldap3
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.rules import IRule
from public import public
from zope.interface import implementer

from mailman_ldaprecipient_plugin.ldap import find_list_group


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

        ldap_list = find_list_group(mlist)
        if ldap_list is None:
            # Not an LDAP based list. Let Original Function handle it
            return self._plugin.original_member_moderation_rule.check(mlist, msg, msgdata)

        # The MemberModeration rule misses unconditionally if any of the
        # senders are banned.
        ban_manager = IBanManager(mlist)
        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False

        for sender in msg.senders:
            if sender in ldap_list['member_emails']:
                # A sender is Group member
                break
        else:
            # No sender is a member, drop to Original function, maybe they are a direct memeber
            return self._plugin.original_member_moderation_rule.check(mlist, msg, msgdata)

        # Use default member action, as LDAP doesn't hold Action Information
        action = mlist.default_member_action

        # Taken from original function
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
        # We should not come to here but drop to original function just in case
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

        ldap_list = find_list_group(mlist)
        if ldap_list is None:
            # Not an LDAP based list. Let Original Function handle it
            return self._plugin.original_nonmember_moderation_rule.check(mlist, msg, msgdata)

        ban_manager = IBanManager(mlist)

        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False
        if len(msg.senders) == 0:
            # there are no sender? let the original nonmember-hook do it's magic
            return self._plugin.original_nonmember_moderation_rule.check(mlist, msg, msgdata)

        # Every sender email must be a member or nonmember directly.  If it is
        # neither, make the email a nonmembers.
        isnonmember = []
        for sender in msg.senders:
            isnonmember.append(sender not in ldap_list['member_emails'])

        if min(isnonmember): # There are only non-members
            # Senders are non-member from LDAP view, however they still might be a direct member
            # let the original nonmember-hook handle that
            return self._plugin.original_nonmember_moderation_rule.check(mlist, msg, msgdata)

        # Sender is a member, i.e. this rule doesn't match
        return False