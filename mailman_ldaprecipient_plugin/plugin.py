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

    def __init__(self):
        for name, section in config.plugin_configs:
            # print(name, section)
            if name == "mailman_ldaprecipient_plugin":
                cf = configparser.ConfigParser()
                cf.read(section.configuration)

                self.ldap_uri = "ldap_uri" in cf["ldap"] and cf["ldap"]["ldap_uri"] or None
                self.ldap_port = "ldap_port" in cf["ldap"] and cf["ldap"]["ldap_port"] or None
                self.ldap_bind_dn = "ldap_bind_dn" in cf["ldap"] and cf["ldap"]["ldap_bind_dn"] or None
                self.ldap_bind_pass = "ldap_bind_pass" in cf["ldap"] and cf["ldap"]["ldap_bind_pass"] or None
                self.ldap_group_base = "ldap_group_base" in cf["ldap"] and cf["ldap"]["ldap_group_base"] or None
                self.ldap_user_base = "ldap_user_base" in cf["ldap"] and cf["ldap"]["ldap_user_base"] or None
                self.ldap_tls_cert = "ldap_tls_cert" in cf["ldap"] and cf["ldap"]["ldap_tls_cert"] or None
                self.ldap_match_listid_attr = "ldap_match_listid_attr" in cf["ldap"] and cf["ldap"][
                    "ldap_match_listid_attr"] or "listId"
                break
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