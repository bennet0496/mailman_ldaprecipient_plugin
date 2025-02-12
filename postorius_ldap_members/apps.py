from django.apps import AppConfig

class PostoriusLdapMembersConfig(AppConfig):
    name = "postorius_ldap_members"
    verbose_name = "Mailing List LDAP members"

    def ready(self):
        from django.urls import re_path
        import postorius.urls
        from .views import LdapListMembersViews

        for i, p in enumerate(postorius.urls.list_patterns):
            print(p)
            if p.name == "list_members":
                print(p)
                # del postorius.urls.list_patterns[i]
                postorius.urls.list_patterns[i] = re_path(r'^members/(?P<role>\w+)/$', LdapListMembersViews.as_view(), name='list_members',)
