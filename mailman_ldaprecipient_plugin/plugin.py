from public import public
from zope.interface import implementer
from mailman.interfaces.plugin import IPlugin

@public
@implementer(IPlugin)
class LdapRecipientPlugin:
    def pre_hook(self):
        pass

    def post_hook(self):
        pass

    @property
    def resource(self):
        return None