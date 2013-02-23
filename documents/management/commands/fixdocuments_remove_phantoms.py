# -*- encoding: utf-8 -*-

from django.core.management.base import NoArgsCommand
from django.db.models import get_models, F

from documents.models import Document
from documents.management.commands.documentscheck import \
        info, warning, set_options


def fix_model(model):
    mn = model.__name__
    info('fixing model : ' + mn)

    c = model.objects.filter(document_start__gte=F('document_end')).count()
    if c:
        model.objects.filter(document_start__gte=F('document_end')).delete()
        warning(mn + ': %d phantom document(s) removed' % c)
    else:
        info(mn + ': no phantom documents found')


def fix(out, err, **options):
    set_options(out, err, **options)
    for m in get_models():
        if issubclass(m, Document):
            fix_model(m)


class Command(NoArgsCommand):
    help = 'Remove all records with document_start >= document_end ' \
            'on all Document subclasses'

    def handle_noargs(self, **options):
        fix(self.stdout, self.stderr, **options)

