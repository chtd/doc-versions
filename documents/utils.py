# -*- encoding: utf-8 -*-


def vlist_blocker(vlist, blocksize=100000, bisect=None, log=None):
    ''' 
    Iterator on values_list, that reads from the database in block

    :param vlist: QuerySet, there should be an index on the first field
        of order_by clause.
    :param blocksize: the size of the block(the number of entries to 
        be queried)
    :param bisect: function that gives the average of two values of the 
        first field in order_by clause lambda x,y :(x+y)/2 by default
    :param log: logging function(accepts one string)
    '''
    if bisect is None:
        bisect = lambda x, y:(x + y) / 2
    model = vlist.model
    field_name = vlist.query.order_by[0].lstrip('-')
    field_index = vlist._fields.index(field_name)
    to_python = model._meta.get_field(field_name).to_python

    if log is not None:
        log('using index for model %s, field name: "%s" index: %d ...'
              % (model, field_name, field_index))
    blocks = []
    try: fmin = to_python(vlist[0][field_index])
    except IndexError: return
    cmin = vlist.filter(**{field_name: fmin}).count()
    blocks.append((fmin, cmin))
    c = vlist.count()
    if c <= blocksize:                 # process as is - little data
        if log is not None:
            log('low size %d - simple processing(%s)' % (c, model))
        for d in vlist.iterator():
            yield d
        return
    blocks.append((to_python(vlist.reverse()[0][field_index]), c))
    _bisect_blocks(blocks, blocksize, vlist, field_name, bisect, log)
    for d in _blocks_iterator(blocks, vlist, field_name, model, log):
        yield d


def qset_blocker(qset, blocksize=100000, bisect=None, log=None):
    ''' 
    Iterator on QuerySet, that reads from the database in block

    :param qset: QuerySet, there should be an index on the first field
        of order_by clause.
    :param blocksize: the size of the block(the number of entries to 
        be queried)
    :param bisect: function that gives the average of two values of the 
        first field in order_by clause lambda x,y :(x+y)/2 by default
    :param log: logging function(accepts one string) FIXME - use logging!
    '''
    if bisect is None:
        bisect = lambda x, y:(x + y) / 2
    model = qset.model
    field_name = qset.query.order_by[0].lstrip('-')

    if log is not None:
        log('creating index for model %s, field name : "%s" ...'
              % (model, field_name))
    blocks = []
    try: fmin = getattr(qset[0], field_name)
    except IndexError: return
    cmin = qset.filter(**{field_name: fmin}).count()
    blocks.append((fmin, cmin))
    c = qset.count()
    if c <= blocksize:                 # process as is - little data
        if log is not None:
            log('low size %d - simple processing(%s)' % (c, model))
        for d in qset.iterator():
            yield d
        return
    blocks.append((getattr(qset.reverse()[0], field_name), c))
    _bisect_blocks(blocks, blocksize, qset, field_name, bisect, log)
    for d in _blocks_iterator(blocks, qset, field_name, model, log):
        yield d


def _blocks_iterator(blocks, qset, field_name, model, log):
    for i,(lim, val) in enumerate(blocks):
        if log is not None:
            log('block: %d, counter: %d, label: %s(%s)' % (i, val, lim, model))
        d = {field_name + '__lte': lim}
        if i:
            d[field_name + '__gt'] = blocks[i - 1][0]
        for dd in qset.filter(**d).iterator():
            yield dd


def _bisect_blocks(blocks, blocksize, qset, field_name, bisect, log):
    if log is not None:
        log(' min : %s , max : %s total : %d' %
                (blocks[0][0], blocks[1][0], blocks[1][1]))
    while True:
        ls, vs = blocks[0]
        for i,(le, ve) in enumerate(blocks):
            if i >= 2 and ve - blocks[i - 2][1] < blocksize:
                del blocks[i - 1]
                break
            if ve - vs > blocksize:
                lm = bisect(ls, le)
                if ls < lm < le:
                    vm = qset.filter(**{
                        field_name + '__lte': lm,
                        field_name + '__gt': ls,
                        }).count() + vs
                    blocks.insert(i,(lm, vm))
                    if log is not None:
                        log('total blocks: %d, current: %d, '\
                            'value: %s, label: %s' %(len(blocks), i, vm, lm))
                    break
            ls, vs = le, ve
        else:
            break
    if log is not None:
        log('index created for %d blocks' % len(blocks))
