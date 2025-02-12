from mailman.config import config
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.plugin import IPlugin
from mailman.rest.helpers import okay, etag, bad_request
from mailman.rest.validator import Validator
from public import public
from zope.component import getUtility
from zope.interface import implementer
from mailman_ldaprecipient_plugin.ldap import find_list_group, LdapMemberCollection


class _FoundLdapMembers(LdapMemberCollection):
    def __init__(self, members):
        self._members = members

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return self._members

@public
class RESTMembers:
    def on_get(self, request, response):
        validator = Validator(
            list_id=str,
            # Allow pagination.
            page=int,
            count=int,
            _optional=('page', 'count'))

        try:
            data = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return

        mlist = getUtility(IListManager).get(data["list_id"])
        ldap_members = [
            {
                'display_name': m['displayName'][0],
                'email': m['mail'][0],
                'list_id': data['list_id'],
                'role': 'ldap',
                'self_link': '',
             }
            for m in find_list_group(mlist, populate_member_emails=False, populate_members=True)['members']]


        resource = _FoundLdapMembers(ldap_members)

        try:
            collection = resource._make_collection(request, None)
        except ValueError as ex:
            bad_request(response, str(ex))
            return
        okay(response, etag(collection))

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
        return RESTMembers()