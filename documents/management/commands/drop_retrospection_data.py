# -*- encoding: utf-8 -*-

from datetime import datetime

from django.core.management.base import NoArgsCommand
from django.db.models import get_models
from django.db import transaction

from documents.models import Document, FUTURE
from documents.management.commands.documentscheck import \
        info, warning, set_options


@transaction.commit_on_success
def fix_model(model):
    mn = model.__name__
    info('fixing model : ' + mn)

    oc = model.objects.count()
    info(mn + ' %d records total' % oc)
    model.objects.filter(document_end__lt=FUTURE).delete()
    c = oc - model.objects.update(document_start=datetime.min)
    if c:
        warning(mn + ': %d document(s) removed' % c)
    else:
        info(mn + ': no documents removed')


def fix(out, err, **options):
    set_options(out, err, **options)
    for m in get_models():
        if issubclass(m, Document):
            fix_model(m)


class Command(NoArgsCommand):
    help = 'Remove version history from all document subclasses'

    def handle_noargs(self, **options):
        fix(self.stdout, self.stderr, **options)

