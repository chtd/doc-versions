# -*- encoding: utf-8 -*-

from datetime import datetime

from django.core.management.base import NoArgsCommand
from django.db.models import get_models

from documents.models import Document, FUTURE
from documents.management.commands.documentscheck import \
        info, warning, set_options


def fix_model (model):
    mn = model.__name__
    info('fixing model : ' + mn)

    c = model.objects.filter(document_end__gt=FUTURE)\
            .exclude(document_end=datetime.max)\
            .update(document_end=datetime.max)
    if c:
        warning(mn + ': %d document(s) ending after FUTURE'
                     ' and !=datetime.max fixed' % c)
    else:
        info(mn + ': no documents ending after FUTURE'
                  ' and !=datetime.max')


def fix(out, err, **options):
    set_options(out, err, **options)
    for m in get_models():
        if issubclass(m, Document):
            fix_model(m)


class Command(NoArgsCommand):
    help = 'Fix document_end greater than datetime.max on all ' \
           'Document subclasses'

    def handle_noargs(self, **options):
        fix(self.stdout, self.stderr, **options)

