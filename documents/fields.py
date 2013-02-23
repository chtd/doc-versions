# -*- encoding: utf-8 -*-

from django.db import models

from documents.models import Document


class DocumentForeignKey(models.IntegerField):
    '''
    Class for links to documents.

    Currently only useful for documenting intent and little error checking 
    '''

    def __init__(self, to, **kwargs):
        assert isinstance(to, basestring) or issubclass(to, Document)
        super(DocumentForeignKey, self).__init__(**kwargs.copy())
