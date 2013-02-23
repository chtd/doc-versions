# -*- encoding: utf-8 -*-

'Check documents integrity'

from datetime import datetime

from django.core.management.base import NoArgsCommand
from django.db.models import get_models, F

from documents.models import Document, FUTURE
from documents.utils import vlist_blocker


OUT = None                              # protocol (all)
ERR = None                              # only errors
VERBOSITY = 1                           # 0/1/2


def info(message):
    if VERBOSITY > 1:
        OUT.write('i ' + message + '\n')


def warning(message):
    if VERBOSITY:
        OUT.write('w ' + message + '\n')


def error(message):
    ERR.write('e ' + message + '\n')
    if VERBOSITY:
        OUT.write('e ' + message + '\n')


def check_model(model):
    mn = model.__name__
    now = datetime.now()
    info('checking model : ' + mn)

    # start is in the future
    c = model.objects.filter(document_start__gt=now).count()
    if c:
        warning(mn + ': %d document(s) starting in future' % c)
    else:
        info(mn + ': no documents starting in future')

    # end is in the future
    c = model.objects.filter(document_end__range=(now, FUTURE)).count()
    if c:
        warning(mn + ': %d document(s) ending in future' % c)
    else:
        info(mn + ': no documents ending in future')

    # end is greater than datetime.max
    c = model.objects.filter(document_end__gt=datetime.max).count()
    if c:
        warning(mn + ': %d document(s) ending after datetime.max' % c)
    else:
        info(mn + ': no documents ending after datetime.max')

    # check direction, start <= end
    c = 0
    for document_id__id in model.objects\
            .filter(document_end__lt=F('document_start'))\
            .order_by('document_id', 'id')\
            .values_list('document_id', 'id'):
        error(mn + ': document_id: %d, id: %d - start > end' % document_id__id)
        c += 1
    if c:
        error(mn + ': total %d illegal record(s) (start>end)' % c)
    else:
        info(mn + ': no illegal records found (start>end)')

    # phantom
    c = model.objects.filter(document_end=F('document_start')).count()
    if c:
        warning(mn + ': %d phantom document(s) (start=end)' % c)
    else:
        info(mn + ': no phantom documents (start=end)')
    # overlapping intervals and holes in history (do using aggregation)
    # tn = model._meta.db_table
    # c = 0
    # for o in model.objects.extra(
    #     select={'overlapping_id': 's.id'},
    #     tables=['"%s" as "s"' % tn],
    #     where=['"%s".document_id=s.document_id' % tn,
    #            '"%s".id<s.id' % tn,
    #            '"%s".document_start<s.document_end' % tn,
    #            's.document_start<"%s".document_end' % tn]):
    #     error(mn+': document_id: %d, id: %d overlapped by %d' %
    #           (o.document_id, o.id, o.overlapping_id))
    #     c += 1
    # if c: error(mn + ': total %d overlapping accident(s)' % c)
    # else: info(mn + ': no overlapping accidents')

    h = 0    # hole counter
    c = 0    # overlapped counter in the past
    ec = 0   # now
    cmin, cmax = datetime.max, datetime.min  # bad interval in the past
    ecmin = datetime.max                     # starting from, till now
    pid = pdid = pe = None # past values
    for id_, did, s, e in vlist_blocker(model.objects.all(). \
        order_by('document_id', 'document_start', 'document_end'). \
        values_list('id', 'document_id',
                      'document_start', 'document_end'),
                      log=info):
        if pdid == did:
            if s < pe:
                em = min(pe, e)
                if em > FUTURE:
                    warning(mn + ': document_id: %d, id: %d overlapped by %d'
                              ' since %s' % (did, pid, id_, s))
                    if ecmin > s:
                        ecmin = s
                    ec += 1
                elif em != s:
                    info(mn + ': document_id: %d, id: %d overlapped by %d'
                           ' (%s,%s)' % (did, pid, id_, s, em))
                    if cmin > s:
                        cmin = s
                    if cmax < em:
                        cmax = em
                    c += 1
            elif s > pe:
                info(mn + ': document_id: %d, hole between ids: %d %d' %
                       (did, pid, id_))
                h += 1
        pid, pdid, pe = id_, did, e
    if c:
        warning(mn + ': total %d overlapping accident(s) between (%s,%s)' %
                (c, cmin, cmax))
    else:
        info(mn + ': no overlapping accidents in the past')
    if ec:
        error(mn + ': total %d overlapping accident(s) since %s' % (ec, ecmin))
    else:
        info(mn + ': no overlapping accidents now')
    if h:
        warning(mn + ': total %d hole(s)' % h)
    else:
        info(mn + ': no holes')


def set_options(out, err, **options):
    global OUT, ERR, VERBOSITY
    OUT, ERR = out, err
    VERBOSITY = int(options['verbosity'])


def check(out, err, **options):
    set_options(out, err, **options)
    for m in get_models():
        if issubclass(m, Document):
            check_model(m)


class Command(NoArgsCommand):
    help = 'Document subclasses integrity check'

    def handle_noargs(self, **options):
        check(self.stdout, self.stderr, **options)

