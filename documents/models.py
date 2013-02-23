# -*- encoding: utf-8 -*-

from datetime import datetime

from django.db import models, transaction, connection, DEFAULT_DB_ALIAS
from django.shortcuts import get_object_or_404
from django.conf import settings

from documents.retrospection import now


# far enough in the future, but less then document.max
FUTURE = datetime(3000, 1, 1)


class DocumentPartNowManager(models.Manager):
    ''' 
    QuerySet for parts of the document at current time
    '''

    def get_query_set(self):
        dt = now()
        tm = self.model.to_master()
        d = { tm + '__document_start__lte': dt,
              tm + '__document_end__gt': dt}
        return super(DocumentPartNowManager, self).get_query_set().filter(**d)


class DocumentNowManager(models.Manager):
    def get_query_set(self):
        dt = now()
        return super(DocumentNowManager, self).get_query_set().filter(
            document_start__lte=dt, document_end__gt=dt)


class DocumentPart(models.Model):
    class ConfigurationError(Exception):
        pass

    class Meta:
        abstract = True

    @classmethod
    def document_get(cls, dt, **kwargs):
        return cls.at(dt, **kwargs).get()

    @classmethod
    def to_master(cls):
        '''
        Calculate prefix for filtering times in "at" method.
        '''
        raise NotImplementedError

    @classmethod
    def at(cls, dt, **kwargs):
        ''' 
        QuerySet for document parts at given dt 
        '''
        tm = cls.to_master()
        d = { tm + '__document_start__lte': dt,
              tm + '__document_end__gt': dt}
        d.update(kwargs)
        return cls.objects.filter(**d)

    def history(self, **kwargs):
        '''
        QuerySet for the document history in reverse chronological order
        '''
        cls = self.__class__
        tm = cls.to_master()
        document = self
        for r in tm.split('__'):
            document = getattr(document, r)
        d = { tm + '__document_id': document.document_id,
              # to exclude equal start and end
              tm + '__document_start__lt': models.F(tm + '__document_end')}
        d.update(kwargs)
        return cls.objects.filter(**d).order_by('-' + tm + '__document_start')

    objects = models.Manager()      # use the default one
    now = DocumentPartNowManager()  # at current time


class Document(DocumentPart):
    class Meta:
        abstract = True

    document_start = models.DateTimeField(
            'Time of the start of this version',
            editable=False, db_index=True)
    document_end = models.DateTimeField(
            'Time of the end of this version',
            editable=False, db_index=True)
    document_id = models.IntegerField(
            'Document identifier',
            editable=False, default=0, db_index=True)

    class ChangedAlready(Exception):
        pass

    objects = models.Manager()  # use the default one
    now = DocumentNowManager()  # at current time

    def document_save(self, document_start=None):
        '''
        Save the new version of the document

        :param id: if given, should be the identifier of the last version,
           from which the current one is beeing created. If this condition
           is violated, we throw ChangedAlready exception. You should check
           for this exception to ensure that there are not concurrent edits 
           to the same document.

        :param document_start: equals datetime.now() by default - 
           will be the time of the start of new version, and the end of the
           old version. 
           
        Should be overriden in compound documents to get consistent verions 
       (as different parts might be saved at different times), and links
        from the old parts might need updating too.
        '''
        if self.document_start is not None and document_start is not None:
            assert self.document_start <= document_start
        self.document_start = document_start or datetime.now()
        self.document_end = datetime.max
        if self.document_id and self.id:
            if self.__class__.objects\
                    .filter(id=self.id,
                            document_id=self.document_id,
                            document_end__gt=FUTURE)\
                    .update(document_end=self.document_start) != 1:
                raise self.ChangedAlready()
        elif self.document_id:
            self.__class__.objects\
                .filter(document_id=self.document_id,
                         document_end__gt=FUTURE)\
                .update(document_end=self.document_start)
        self.id = self.pk = None  # for inheriting models, where pk != id
        self.save(force_insert=True)
        if self.document_id == 0:
            self.document_id = self.new_document_id()
            self.save(force_update=True)

    def save_now(self):
        self.document_save(now())

    def new_document_id(self):
        return self.id

    def document_delete(self, delete_time=None):
        return self.__class__.objects.filter(
                document_id=self.document_id, document_end__gt=FUTURE)\
               .update(document_end=delete_time or datetime.now())

    def delete_now(self):
        return self.document_delete(now())

    @classmethod
    def document_get_or_404(cls, dt, **kwargs):
        return get_object_or_404(
                cls, document_start__lte=dt, document_end__gt=dt, **kwargs)

    @classmethod
    def at(cls, dt, **kwargs):
        return cls.objects.filter(
                document_start__lte=dt, document_end__gt=dt, **kwargs)

    def history(self, **kwargs):
        '''
        QuerySet for the document history in reverse chronological order
        '''
        return self.__class__.objects.filter(
            document_id=self.document_id,
            document_start__lt=models.F('document_end'), **kwargs
            ).order_by('-document_start')

    def document_restore(self, document_start=None):
        ''' 
        Restore the document from the previous verions(in other words,
        make previous verion the current one).

        :param document_start: the start of new version.
        
        The whole method should be overriden for compound documents to get
        a consistent version - apart from document_start, we must update
        links to this document from the objects that were linking to the
        previous version.
        '''
        assert self.document_id
        if self.document_end > FUTURE:
            return  # already the last version
        last = self.__class__.objects.filter(
            document_id=self.document_id).latest('document_end')
        assert document_start is None or last.document_start < document_start
        self.document_start = document_start or datetime.now()
        self.document_end = datetime.max
        self.__class__.objects.filter(
            document_id=self.document_id, document_end__gt=FUTURE).update(
            document_end=self.document_start)
        self.id = self.pk = None  # for inheriting models, where pk != id
        self.save(force_insert=True)

    def restore_now(self):
        self.document_restore(now())

    @classmethod
    def bulk_documents_save(cls, documents, document_start=None):
        '''
        Save the new versions of documents in bulk
        '''
        assert cls._meta.pk.name == u'id'

        documents = list(documents)
        if document_start is None:
            document_start = datetime.now()

        with_document_id_and_id = []
        with_document_id = []

        for d in documents:

            assert d.__class__ is cls

            if d.document_start is not None:
                assert d.document_start <= document_start

            d.document_start = document_start
            d.document_end = datetime.max

            if d.document_id and d.id:
                with_document_id_and_id.append(d.id)
            elif d.document_id:
                with_document_id.append(d.document_id)

        if with_document_id_and_id:
            if cls.objects\
                    .filter(id__in=with_document_id_and_id,
                            document_end__gt=FUTURE)\
                    .update(document_end=document_start) != \
                        len(with_document_id_and_id):
                raise cls.ChangedAlready()

        if with_document_id:
            cls.objects\
                    .filter(document_id__in=with_document_id,
                            document_end__gt=FUTURE)\
                    .update(document_end=document_start)

        ids = cls.bulk_ids(len(documents))
        for id, d in zip(ids, documents):
            d.id = id
            if not d.document_id:
                d.document_id = d.new_document_id()
        cls.bulk_insert(documents)

    @classmethod
    def bulk_save_now(cls, documents):
        cls.bulk_documents_save(documents, now())

    @classmethod
    def bulk_documents_delete(cls, documents, delete_time=None):
        if not documents:
            return 0
        return cls.objects.filter(
                document_id__in=[d.document_id for d in documents],
                document_end__gt=FUTURE)\
               .update(document_end=delete_time or datetime.now())

    @classmethod
    def bulk_delete_now(cls, documents):
        return cls.bulk_documents_delete(documents, now())

    @classmethod
    def bulk_ids(cls, n):
        assert n >= 0
        if n == 0:
            return []
        if 'postgresql' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
            cursor = connection.cursor()
            sql = "select nextval('%s_id_seq') from generate_series(1,%d)"\
                    % (cls._meta.db_table, n)
            cursor.execute(sql)
            return [int(r[0]) for r in cursor]
        elif 'sqlite' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
            m = cls.objects.aggregate(models.Max('id'))['id__max']
            if m is None:
                m = 0
            return range(m + 1, n + m + 1)
        raise NotImplementedError

    @classmethod
    def bulk_insert(cls, documents):
        if not documents:
            return
        if hasattr(cls.objects, 'bulk_create'):  # added in Django 1.4
            cls.objects.bulk_create(documents)
        else:
            cls._bulk_insert_custom(documents)

    @classmethod
    def _bulk_insert_custom(cls, documents):
        qn = connection.ops.quote_name
        cursor = connection.cursor()
        fields = cls._meta.fields
        flds = ', '.join(qn(f.column) for f in fields)
        # sqlite INSERT can not process many values in one query
        if 'sqlite' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
            values_list = [[f.get_db_prep_save(getattr(d, f.attname))
                              for f in fields] for d in documents]
            arg_string = '(' + ', '.join(['%s'] * len(fields)) + ')'
            sql = 'INSERT INTO %s(%s) VALUES %s' \
                    % (cls._meta.db_table, flds, arg_string)
            cursor.executemany(sql, values_list)
        else:
            values_list = [f.get_db_prep_save(getattr(d, f.attname))
                            for d in documents for f in fields]
            arg_string = ', '.join(
                    ['(' + ', '.join(['%s'] * len(fields)) + ')']
                    * len(documents))
            sql = 'INSERT INTO %s(%s) VALUES %s' \
                    % (cls._meta.db_table, flds, arg_string)
            cursor.execute(sql, values_list)
        cursor.close()
        transaction.commit_unless_managed()

    @classmethod
    def to_master(cls):
        # should not be called
        assert False, 'to_master of the main document should not be called'


class DocumentPartF(DocumentPart):
    '''
    A part of the versioned document, that has links TO it::

        Document -> DocumentPart
    '''

    class Meta:
        abstract = True

    @classmethod
    def to_master(cls):
        '''
        Calculate prefix for filtering times in "at" method.

        Override if there are links to/from other documents.
        '''
        o = cls._meta
        ro = [r for r in o.get_all_related_objects()
                if isinstance(r.field, models.ForeignKey)]
        d = [r for r in ro if issubclass(r.model, DocumentPart)]
        if len(d) == 1:
            d = d[0]
            if issubclass(d.model, Document):
                return d.var_name
            return d.var_name + '__' + d.model.to_master()
        raise cls.ConfigurationError('Master not found - redefine')


class DocumentPartB(DocumentPart):
    '''
    A part of the versioned document, that has links FROM it::

        Document <- DocumentPart
    '''

    class Meta:
        abstract = True

    @classmethod
    def to_master(cls):
        '''
        Calculate prefix for filtering times in "at" method.

        Override if there are links to/from other documents.
        '''
        o = cls._meta
        fs = [f for f in o.fields if isinstance(f, models.ForeignKey)]
        d = [f for f in fs
              if issubclass(f.related.parent_model, DocumentPart)]
        if len(d) == 1:
            d = d[0]
            if issubclass(d.related.parent_model, Document):
                return d.name
            return d.name + '__' + d.related.parent_model.to_master()
        raise cls.ConfigurationError('Master not found - redefine')
