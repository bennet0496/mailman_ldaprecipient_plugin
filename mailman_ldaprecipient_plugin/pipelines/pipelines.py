from public import public
from mailman.interfaces.pipeline import IPipeline
from mailman.pipelines.base import BasePipeline
#from mailman.pipelines.builtin import PostingPipeline
from zope.interface import implementer

# Pipelines are list of "handlers"
# https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/handlers/docs/handlers.html

# The Pipelines has to be an implementation of the IPipeline interface
# https://gitlab.com/mailman/mailman/-/blob/master/src/mailman/interfaces/pipeline.py#L63

# Here are some example of built-in pipelines that are used by default in Mailman.
# https://gitlab.com/mailman/mailman/-/blob/master/src/mailman/pipelines/builtin.py

@public
@implementer(IPipeline)
class MailLdapRecipientPipeline(BasePipeline):

    # The name of the pipeline should be unique.
    name = 'mail-ldap-recipient-pipeline'

    # Briefly describe the pipeline so it can be shown in web frontends to users when choosing a pipeline.
    description = 'Add LDAP Recipients and modify headers pipeline'

    # List of handlers, in the correct order, to be used for processing the email.
    # See: https://gitlab.com/mailman/mailman/-/blob/master/src/mailman/pipelines/builtin.py
    # You can add your handler at the end if the order is correct for your use case
    # _default_handlers = PostingPipeline._default_handlers + ('mailman-after-sent-handler')
    _default_handlers = (
        'validate-authenticity',
        'mime-delete',
        'tagger',
        'member-recipients',
        'ldap-recipients',
        'avoid-duplicates',
        'cleanse',
        'cleanse-dkim',
        'cook-headers',
        'subject-prefix',
        'rfc-2369',
        'to-archive',
        'to-digest',
        'to-usenet',
        'after-delivery',
        'acknowledge',
        # All decoration is now done in delivery.
        # 'decorate',
        'dmarc',
        # Message decoration in delivery can break an arc signature, so sign
        # in delivery after decorating.
        # 'arc-sign',
        # Add the Sender header
        'mailman-sender-handler',
        'mailman-headers-handler',
        # Send it
        'to-outgoing',
    )
