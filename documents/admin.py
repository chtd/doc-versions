# -*- encoding: utf-8 -*-

from datetime import datetime

from django import template, forms
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.admin import ModelAdmin
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.util import unquote
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.text import capfirst

from documents.fields import DocumentForeignKey
from documents.models import Document


class DocumentModelAdmin(ModelAdmin):
    ''' 
    Tweaked admin class to work with documents:

    * show only the latest verions
    * view verion history, showing changed fields and change authors
    * only last versions in DocumentForeignKey and m2m to other documents
    '''

    def save_model(self, request, document, form, change):
        document.id = None
        document.document_save()
    # TODO - redefine save_formset as well

    def get_form(self, request, obj=None, **kwargs):
        form = super(DocumentModelAdmin, self).get_form(request, obj, **kwargs)
        for _, field in form.base_fields.iteritems():
            if isinstance(field, forms.ModelMultipleChoiceField) and \
                    issubclass(field.queryset.model, Document):
                now = datetime.now()
                field.queryset = field.queryset.filter(
                    document_start__lte=now, document_end__gt=now)
        return form

    def queryset(self, request):
        now = datetime.now()
        return super(DocumentModelAdmin, self).queryset(request) \
             .filter(document_start__lte=now, document_end__gt=now).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if isinstance(db_field, DocumentForeignKey):
            if 'queryset' not in kwargs:
                kwargs['queryset'] = db_field.rel.to.at(datetime.now())
        return super(DocumentModelAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def history_view(self, request, object_id, extra_context=None):
        ''' 
        Version history - a mix of django and documents history
        '''
        model = self.model
        obj = get_object_or_404(model, pk=unquote(object_id))
        opts = model._meta
        app_label = opts.app_label
        action_list = LogEntry.objects.filter(
            object_id=object_id,
            content_type__id__exact=\
                    ContentType.objects.get_for_model(model).id)\
            .select_related().order_by('action_time')
        fields = [f for f in opts.fields if f.name not in 
                  ('id', 'document_start', 'document_end', 'document_id')]
        context = {
            'title': _('Change history: %s') % force_unicode(obj),
            'versions': self._full_action_list(
                obj, action_list, [f.name for f in fields]),
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'field_titles': [f.verbose_name for f in fields],
            'object': obj,
            'root_path': self.admin_site.root_path,
            'app_label': app_label,
        }
        return render_to_response(
            'document_history.html', context,
            context_instance=template.RequestContext(
                request, current_app=self.admin_site.name))

    def _full_action_list(self, obj, action_list, fields):
        ''' 
        Try to build a correspondence between django action_list and 
        document version, with some precision.
        '''
        versions = list(self.model.objects.filter(document_id=obj.document_id)\
                .order_by('-document_start'))
        with_sec_precision = lambda d: datetime(
            d.year, d.month, d.day, d.hour, d.minute, d.second)
        actions_on_seconds = dict((with_sec_precision(a.action_time), a) 
                for a in action_list)
        found_actions = set()
        for v in versions:
            v.action = actions_on_seconds.get(
                    with_sec_precision(v.document_start))
            v.fields = [getattr(v, f) for f in fields]
            if v.action:
                found_actions.add(v.action)
        for a in action_list:
            # find actions that have no corresponding versions
            if a not in found_actions:
                a.document_start = a.action_time
                a.action = a
                a.fields = ['' for _ in fields]
                versions.append(a)
        return reversed(sorted(versions, key=lambda v: v.document_start))

