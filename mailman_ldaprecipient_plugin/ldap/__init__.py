import configparser
import json
from functools import lru_cache

import ldap3
from mailman.config import config as mmconfig
from mailman.interfaces.mailinglist import IMailingList
from mailman.rest.helpers import CollectionMixin, bad_request, okay, etag
from mailman.rest.validator import Validator
from zope.component import getUtility


@lru_cache
def get_config():
    # plugin = mmconfig.plugins['mailman_ldaprecipient_plugin']
    for name, section in mmconfig.plugin_configs:
        # print(name, section)
        if name == "mailman_ldaprecipient_plugin":
            cf = configparser.ConfigParser()
            cf.read(section.configuration)
            return {
                'ldap_uri': "ldap_uri" in cf["ldap"] and cf["ldap"]["ldap_uri"] or None,
                'ldap_port': "ldap_port" in cf["ldap"] and cf["ldap"]["ldap_port"] or None,
                'ldap_bind_dn': "ldap_bind_dn" in cf["ldap"] and cf["ldap"]["ldap_bind_dn"] or None,
                'ldap_bind_pass': "ldap_bind_pass" in cf["ldap"] and cf["ldap"]["ldap_bind_pass"] or None,
                'ldap_group_base': "ldap_group_base" in cf["ldap"] and cf["ldap"]["ldap_group_base"] or None,
                'ldap_user_base': "ldap_user_base" in cf["ldap"] and cf["ldap"]["ldap_user_base"] or None,
                'ldap_tls_cert': "ldap_tls_cert" in cf["ldap"] and cf["ldap"]["ldap_tls_cert"] or None,
                'ldap_starttls': "ldap_starttls" in cf["ldap"] and (cf["ldap"]["ldap_starttls"].lower() in
                                                                    ['true', '1', 'yes', 't', 'y']) or False,

                'ldap_listid_attr': "ldap_listid_attr" in cf["ldap"] and cf["ldap"][
                    "ldap_listid_attr"] or "listId",
                'ldap_user_mail_attribute': "ldap_user_mail_attribute" in cf["ldap"] and cf["ldap"][
                    'ldap_user_mail_attribute'] or "mail"
            }
    raise RuntimeWarning("LDAP Plugin not configured")


def get_ldap_connection(config = None) -> ldap3.Connection:
    if config is None:
        config = get_config()

    tls = None
    if config['ldap_tls_cert'] is not None:
        tls = ldap3.Tls(ca_certs_file=config['ldap_tls_cert'])
    srv = ldap3.Server(config['ldap_uri'], int(config['ldap_port'] or 389), tls=tls)
    conn = ldap3.Connection(srv, user=config['ldap_bind_dn'], password=config['ldap_bind_pass'])
    if config['ldap_starttls']:
        conn.start_tls()

    conn.bind()
    return conn

def _find_users_by_uid(uids: list, config = None) -> list:
    if config is None:
        config = get_config()

    conn = get_ldap_connection()

    ufilter = ")(uid=".join(uids)
    ufilter = "(|(uid={}))".format(ufilter)

    conn.search(config['ldap_user_base'], ufilter,
                attributes=ldap3.ALL_ATTRIBUTES,
                get_operational_attributes=False)

    return [e.entry_attributes_as_dict for e in conn.entries]

def _find_users_mail_by_uid(uids: list, config = None) -> list:
    mails = []
    for entry in _find_users_by_uid(uids, config):
        mails.extend(entry['mail'])

    return mails

def _find_users_by_memberof(group_dn: str, config=None) -> list:
    if config is None:
        config = get_config()

    conn = get_ldap_connection()

    conn.search(config['ldap_user_base'], '(memberOf={})'.format(group_dn),
                attributes=ldap3.ALL_ATTRIBUTES,
                get_operational_attributes=False)

    return [e.entry_attributes_as_dict for e in conn.entries]

def _find_users_mail_by_memberof(group_dn: str, config=None) -> list:
    mails = []
    for entry in _find_users_by_memberof(group_dn, config):
        mails.extend(entry['mail'])

    return mails

def find_list_group(mlist: IMailingList, populate_member_emails = True, populate_members = False, config = None) -> dict[str, list]|None:
    if config is None:
        config = get_config()

    conn = get_ldap_connection()

    conn.search(config['ldap_group_base'], "({}={}.{})".format(config['ldap_listid_attr'], mlist.list_name, mlist.mail_host),
                attributes=ldap3.ALL_ATTRIBUTES, get_operational_attributes=False)

    if len(conn.entries) == 0:
        return None

    list_groups = {
        'lists': [json.loads(entry.entry_to_json()) for entry in conn.entries],
        'member_emails': [],
        'members': []
    }

    if populate_member_emails or populate_members:
        for entry in conn.entries:
            if "memberUid" in entry.entry_attributes or "posixGroup" in entry.objectClass.values:
                # Posix Group
                if populate_member_emails:
                    list_groups['member_emails'].extend(_find_users_mail_by_uid(entry.memberUid.values, config))
                if populate_members:
                    list_groups['members'].extend(_find_users_by_uid(entry.memberUid.values, config))
            elif "member" in entry.entry_attributes or "groupOfNames" in entry.objectClass.values:
                # Group Of names
                if populate_member_emails:
                    list_groups['member_emails'].extend(_find_users_mail_by_memberof(entry.entry_dn, config))
                if populate_members:
                    list_groups['members'].extend(_find_users_by_memberof(entry.entry_dn, config))

    return list_groups


class _LdapMemberBase(CollectionMixin):
    """Shared base class for member representations."""

    def _resource_as_dict(self, member, fields=None):
        return member

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        raise NotImplementedError


class LdapMemberCollection(_LdapMemberBase):
    """Abstract class for supporting submemberships.

        This is used for example to return a resource representing all the
        memberships of a mailing list, or all memberships for a specific email
        address.
        """

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        raise NotImplementedError
