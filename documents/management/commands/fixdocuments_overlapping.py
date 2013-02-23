# -*- encoding: utf-8 -*-

from datetime import datetime

from django.core.management.base import NoArgsCommand
from django.db.models import get_models

from documents.models import Document, FUTURE
from documents.utils import vlist_blocker
from documents.management.commands.documentscheck import \
        info, warning, set_options


def fix_model (model):
    mn = model.__name__
    info('fixing model : ' + mn)
    pid = pdid = ps = pe = None         # past values
    for id_, did, s, e in vlist_blocker(model.objects.all()\
            .order_by('document_id', 'document_start', 'document_end')\
            .values_list('id', 'document_id', 'document_start', 'document_end'),
            log=info):
        if pdid == did and s < pe:
            if e > FUTURE:
                e = datetime.max
            if pe > FUTURE:
                pe = datetime.max

            if e < pe:
                model.objects.filter(id=id_).delete()
                warning('document_id: %d, id: %d new overlapped interval'
                          ' removed (%s)' % (did, id_, mn))
                continue
            if s > ps:
                model.objects.filter(id=pid).update(document_end=s)
                warning('document_id: %d, id: %d old overlapped interval'
                          ' truncated (%s)' % (did, pid, mn))
            else:
                model.objects.filter(id=pid).delete()
                warning('document_id: %d, id: %d overlapped interval'
                          ' removed (%s)' % (did, pid, mn))
        pid, pdid, ps, pe = id_, did, s, e


def fix(out, err, **options):
    set_options(out, err, **options)
    for m in get_models():
        if issubclass(m, Document):
            fix_model(m)


class Command(NoArgsCommand):
    help = 'Fix overlapping interval errors for Document subclasses'

    def handle_noargs(self, **options):
        fix(self.stdout, self.stderr, **options)

