import configparser

from public import public
from zope.interface import implementer
from mailman.interfaces.plugin import IPlugin
from mailman.config import config

@public
@implementer(IPlugin)
class LdapRecipientPlugin:
    original_member_moderation_rule = None
    original_nonmember_moderation_rule = None

    def pre_hook(self):
        pass

    def post_hook(self):
        self.original_member_moderation_rule = config.rules['member-moderation']
        self.original_nonmember_moderation_rule = config.rules['nonmember-moderation']

        config.rules['member-moderation'] = config.rules['member-moderation-ldap']
        config.rules['nonmember-moderation'] = config.rules['nonmember-moderation-ldap']

    @property
    def resource(self):
        return None