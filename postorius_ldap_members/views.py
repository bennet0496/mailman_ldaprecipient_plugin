from urllib.parse import urlencode

from mailmanclient import Member
from mailmanclient.restbase.page import Page
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django_mailman3.lib.paginator import paginate, MailmanPaginator
from postorius.forms import MemberForm
from postorius.views import list as list_views


class LdapListMembersViews(list_views.ListMembersViews):
    allowed_roles = ['owner', 'moderator', 'member', 'nonmember','ldap']

    def get(self, request, list_id, role):
        """Handle GET for Member view.

        This includes all the membership roles (self.allowed_roles).
        """
        member_form = MemberForm()
        # If the role is misspelled, redirect to the default subscribers.
        if role not in self.allowed_roles:
            return redirect('list_members', list_id, 'member')

        context : dict = {
            'list': self.mailing_list,
            'role': 'member' if role == 'ldap' else role,
            'member_form': member_form,
            'page_title': _('List {}s'.format(role.capitalize())),
            'query': self._prepare_query(request)
        }

        # Warning: role not translatable

        def find_method(count, page):
            return  self.mailing_list.find_members(
                context['query'], role=role, count=count, page=page
            )

        def find_method_ldap(count, page):
            data = {'list_id': list_id}
            return Page(self.mailing_list._connection,
                             'plugins/mailman_ldaprecipient_plugin?{}'.format(urlencode(data, doseq=True)),
                             Member, count, page)

        context['members'] = paginate(
            find_method_ldap if role == 'ldap' else find_method,
            request.GET.get('page', 1),
            request.GET.get('count', 25),
            paginator_class=MailmanPaginator,
        )
        context['page_subtitle'] = '({})'.format(
            context['members'].object_list.total_size
        )
        context['form_action'] = _('Add {}'.format(role))
        if context['query']:
            context['empty_error'] = _(
                'No {}s were found matching the search.'.format(role)
            )
        else:
            context['empty_error'] = _('List has no {}s'.format(role))

        return render(request, 'postorius/lists/members.html', context)