# -*- encoding: utf-8 -*-

from datetime import datetime
from time import sleep

from django.test import TestCase
from django.http import Http404
from django.db import models

from documents.models import Document, DocumentPartF, DocumentPartB
from documents.retrospection import now, set_now
from documents.fields import DocumentForeignKey


# models for doc-test of modified example from django tutorial

class Choice(Document):
    choice = models.CharField(max_length=200)

    def __unicode__(self):
        return self.choice


class Poll(Document):
    question = models.CharField(max_length=200)

    def __unicode__(self):
        return self.question


class PollChoices(DocumentPartB):
    poll = models.ForeignKey(Poll)
    choice = models.ForeignKey(Choice)

    @classmethod
    def to_master(cls):
        return 'poll'


class PollResults(Document):
    poll = models.ForeignKey(Poll)
    choice = models.ForeignKey(Choice)
    votes = models.IntegerField()

    @staticmethod
    def vote(poll_document_id, choice_document_id):
        n = datetime.now()
        p = Poll.document_get(n, document_id=poll_document_id)
        c = Choice.document_get(n, document_id=choice_document_id)
        try:
            v = PollResults.document_get(
                n, poll__document_id=poll_document_id,
                choice__document_id=choice_document_id)
            v.votes += 1
        except PollResults.DoesNotExist:
            v = PollResults(poll=p, choice=c, votes=1)
        v.document_save()
        return v.document_id

polltest = """
# Пока нет голосований
>>> Poll.objects.all()
[]

# Создаем новое
>>> p = Poll(question="Who is who?")

# Сохраняем.
>>> p.document_save()

# Теперь есть id, document_id, document_start и document_end.
>>> p.id
1
>>> p.document_id
1

# Access database columns via Python attributes.
>>> print p.question
Who is who?

>>> p.document_start # doctest: +ELLIPSIS
datetime.datetime(...)

# Give the Poll a couple of Choices.
>>> now = datetime.now()
>>> p = Poll.document_get(now,document_id=1)

# Display any choices from the related object set -- none so far.
>>> PollChoices.at(now)
[]

# Create three choices.
>>> c1 = Choice(choice='President') ; c1.document_save() ; c1
<Choice: President>
>>> c2 = Choice(choice='Agent') ; c2.document_save() ; c2
<Choice: Agent>
>>> c3 = Choice(choice='Gena Crocodile') ; c3.document_save() ; c3
<Choice: Gena Crocodile>

# document_id назначен автоматически:
>>> for c in(c1,c2,c3) : print c.document_id
1
2
3

# Добавим их:
>>> p.document_save() # новая версия
>>> p.pollchoices_set.add( *[ PollChoices(choice=c) for c in(c1,c2,c3) ] ) 

# Голосование:
>>> PollResults.vote( 1 , 1 )
1
>>> PollResults.vote( 1 , 1 )
1
>>> PollResults.vote( 1 , 1 )
1
>>> PollResults.vote( 1 , 2 )
4

# Запомним момент в промежутке(t):
>>> from time import sleep
>>> sleep( 0.1 )
>>> t = datetime.now()
>>> sleep( 0.1 )

>>> PollResults.vote( 1 , 2 )
4
>>> PollResults.vote( 1 , 3 )
6

# Результаты голосования:
>>> for r in PollResults.at( datetime.now() , poll__document_id=1 ) :
...     print r.votes , r.choice.choice
3 President
2 Agent
1 Gena Crocodile

# Ретроспекция(состояние на момент t):
>>> for r in PollResults.at( t , poll__document_id=1 ) :
...     print r.votes , r.choice.choice
3 President
1 Agent
 
# Очистка:
>>> for m in( Choice , Poll , PollChoices , PollResults ) :
...     m.objects.all().delete()
"""

# another modification of the same example (with a link to specific version)


class Poll2(Document):
    question = models.CharField(max_length=200)

    def __unicode__(self):
        return self.question


class Choice2(Document):
    poll = models.ForeignKey(Poll2)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __unicode__(self):
        return self.choice

polltest2 = """
>>> Poll, Choice = Poll2, Choice2

# Пока нет голосований
>>> Poll.objects.all()
[]

# И в текущий момент тоже
>>> Poll.now.all()
[]

>>> p = Poll(question='who is who?')
>>> p.document_save()
>>> p.id
1

>>> p.document_id
1

>>> print p.question
who is who?

>>> p.document_start # doctest: +ELLIPSIS
datetime.datetime(...)

# если не продвинуться по времени, now показывает старое стостояние

>>> Poll.now.count()
0

>>> Poll.objects.count()
1

# продвигаемся вперед по времени

>>> set_now()
>>> Poll.now.count()
1

>>> p = Poll.now.get(document_id=1)
>>> print p
who is who?

# редактируем документ

>>> set_now()
>>> p.question = 'Who is who here?'
>>> p.document_save()

>>> set_now()
>>> p = Poll.now.get(document_id=p.document_id)
>>> print p
Who is who here?

>>> Poll.objects.count()
2

>>> Poll.now.count()
1

# удаляем документ

>>> set_now()
>>> p.document_delete()
1

>>> set_now()
>>> Poll.now.count()
0

>>> Poll.objects.count()
2

# создаем новый вопрос

>>> p = Poll(question='who is who?')
>>> p.document_save()
>>> p.id
3

>>> p.document_id
3

# добавляем варианты ответа

>>> Choice.now.count()
0

>>> Choice(choice='President', poll=p).document_save()
>>> Choice(choice='Agent', poll=p).document_save()
>>> Choice(choice='Gena Crocodile', poll=p).document_save()

>>> set_now()

>>> p.choice2_set.count()
3

>>> p.question = 'who is who? (take 2)'
>>> p.document_save()

>>> set_now()
>>> p.choice2_set.count()
0

# это не то что нам нужно!

#>>> import pdb; pdb.set_trace()
"""

# another modification of the same example (with a link to current version)


class Poll3(Document):
    question = models.CharField(max_length=200)

    def __unicode__(self):
        return self.question


class Choice3(Document):
    poll = DocumentForeignKey(Poll2)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()

    def __unicode__(self):
        return self.choice


# models for unit-tests

class SimpleDocument(Document):
    data = models.IntegerField()

    def __unicode__(self):
        return '%s(%s,%s,%s,%s)' % (
                self.data, self.document_id, self.id,
                self.document_start, self.document_end)


class SimpleDocumentChild(SimpleDocument):
    cdata = models.IntegerField()

    def __unicode__(self):
        return unicode(self.cdata) + ' - ' + \
            super(SimpleDocumentChild, self).__unicode__()


class FPart(DocumentPartF):
    partdata = models.IntegerField()

    def __unicode__(self):
        return '%s,%s' % (self.partdata, self.id)


class DocumentF(Document):
    data = models.IntegerField()
    link = models.OneToOneField(FPart)

    def __unicode__(self):
        return '%s,%s(%s,%s,%s,%s)' % (
                self.data, self.link_id, self.document_id, self.id,
                self.document_start, self.document_end)


class FFPart0(DocumentPartF):
    partdata = models.IntegerField()

    def __unicode__(self):
        return '%s,%s' % (self.partdata, self.id)


class FFPart(DocumentPartF):
    partlink = models.OneToOneField(FFPart0)

    def __unicode__(self):
        return '%s,%s,%s' % (
        self.partdata, self.partlink_id, self.id)


class DocumentFF(Document):
    data = models.IntegerField()
    link = models.OneToOneField(FFPart)

    def __unicode__(self):
        return '%s,%s(%s,%s,%s,%s)' % (
                self.data, self.link_id, self.document_id, self.id,
                self.document_start, self.document_end)


class DocumentB(Document):
    data = models.IntegerField()

    def __unicode__(self):
        return '%s(%s,%s,%s,%s)' % (
                self.data, self.document_id, self.id,
                self.document_start, self.document_end)


class BPart(DocumentPartB):
    partdata = models.IntegerField()
    link = models.ForeignKey(DocumentB)

    def __unicode__(self):
        return '%s,%s(%s)' % (self.partdata, self.link_id, self.id)


class FBPart(DocumentPartF):
    @classmethod
    def to_master(cls):
        return 'documentfb'


class FBPart0(DocumentPartB):
    partlink = models.OneToOneField(FBPart)
    partdata = models.IntegerField()


class DocumentFB(Document):
    data = models.IntegerField()
    link = models.OneToOneField(FBPart)


class DocumentFKSourceString(Document):
    link = DocumentForeignKey('DocumentFKDestination')


class DocumentFKDestination(Document):
    data = models.IntegerField()


class DocumentFKSource(Document):
    link = DocumentForeignKey(DocumentFKDestination)


__test__ = {
    'polltest': polltest,
    'polltest2': polltest2,
    #'polltest3': polltest3,
    }


class SimpleDocumentBulkTest(TestCase):
    def tearDown(self):
        SimpleDocument.objects.all().delete()

    def test_bulk_delete(self):
        d1 = SimpleDocument(data=1)
        d2 = SimpleDocument(data=2)
        d3 = SimpleDocument(data=3)
        SimpleDocument.bulk_documents_save([d1, d2, d3])
        for data in range(1, 4):
            d = SimpleDocument.objects.get(data=data)
            self.assertEqual(d.data, data)
            self.assertEqual(d.document_id, d.id)
            self.assertEqual(d.document_end, datetime.max)
            self.assertTrue(d.document_start <= datetime.now())
        SimpleDocument.bulk_documents_delete([d1, d2, d3])
        for data in range(1, 4):
            self.assertRaises(SimpleDocument.DoesNotExist,
                    SimpleDocument.now.get, data=data)

    def test_document_save_many(self):
        d1 = SimpleDocument(data=1)
        d2 = SimpleDocument(data=2)
        d3 = SimpleDocument(data=3)
        SimpleDocument.bulk_documents_save([d1, d2, d3])
        for data in range(1, 4):
            d = SimpleDocument.objects.get(data=data)
            self.assertEqual(d.data, data)
            self.assertEqual(d.document_id, d.id)
            self.assertEqual(d.document_end, datetime.max)
            self.assertTrue(d.document_start <= datetime.now())

    def test_document_save(self):
        d = SimpleDocument(data=1)
        SimpleDocument.bulk_documents_save([d])
        d = SimpleDocument.objects.get(data=1)
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, d.id)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())

    def test_document_save_1(self):
        d = SimpleDocument(data=1, document_id=123, id=17)
        self.assertRaises(SimpleDocument.ChangedAlready,
                SimpleDocument.bulk_documents_save, [d])

    def test_document_save_2(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        t = datetime.now()
        d.data = 2
        SimpleDocument.bulk_documents_save([d])
        self.assertEqual(
            SimpleDocument.objects.filter(document_id=123).count(), 2)
        d = SimpleDocument.objects.order_by('-id')[0]
        self.assertEqual(d.data, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocument.objects.order_by('id')[0]
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_save_3(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        t = datetime.now()
        d.data = 2
        d.id = None
        SimpleDocument.bulk_documents_save([d])
        self.assertEqual(
                SimpleDocument.objects.filter(document_id=123).count(), 2)
        d = SimpleDocument.objects.order_by('-id')[0]
        self.assertEqual(d.data, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocument.objects.order_by('id')[0]
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_delete(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        t = datetime.now()
        d.document_delete()
        self.assertEqual(
                SimpleDocument.objects.filter(document_id=123).count(), 1)
        d = SimpleDocument.objects.get()
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_get_or_404(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        d = SimpleDocument.document_get_or_404(
                datetime.now(), document_id=123)
        self.assertEqual(d.data, 1)

    def test_document_get_or_404_1(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        self.assertRaises(Http404, SimpleDocument.document_get_or_404,
                datetime.now(), document_id=12)

    def test_document_get(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        d = SimpleDocument.document_get(datetime.now(), document_id=123)
        self.assertEqual(d.data, 1)

    def test_document_get_1(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        self.assertRaises(SimpleDocument.DoesNotExist,
                SimpleDocument.document_get,
                datetime.now(), document_id=12)

    def test_at(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        id1 = d.id
        t = datetime.now()
        sleep(0.001)
        d.data = 2
        SimpleDocument.bulk_documents_save([d])
        id2 = d.id
        self.assertEqual(SimpleDocument.at(t).get().id, id1)
        self.assertEqual(SimpleDocument.at(datetime.now()).get().id, id2)

    def test_history(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        t = datetime.now()
        d.data = 2
        SimpleDocument.bulk_documents_save([d])
        self.assertEqual(d.history().count(), 2)
        self.assertEqual(d.history()[0].data, 2)
        self.assertEqual(d.history()[1].data, 1)

    def test_document_restore(self):
        d = SimpleDocument(data=1, document_id=123)
        SimpleDocument.bulk_documents_save([d])
        t1 = datetime.now()
        sleep(0.001)
        d.data = 2
        SimpleDocument.bulk_documents_save([d])
        t2 = datetime.now()
        sleep(0.001)
        self.assertEqual(SimpleDocument.at(t2).get(document_id=123).data, 2)
        self.assertEqual(SimpleDocument.at(t1).get(document_id=123).data, 1)
        SimpleDocument.at(t1).get(document_id=123).document_restore()
        self.assertEqual(
                SimpleDocument.at(datetime.now()).get(document_id=123).data, 1)
        sleep(0.001)
        SimpleDocument.at(t2).get(document_id=123).document_restore()
        self.assertEqual(
                SimpleDocument.at(datetime.now()).get(document_id=123).data, 2)


class SimpleDocumentTest(TestCase):
    def tearDown(self):
        SimpleDocument.objects.all().delete()

    def test_document_save(self):
        d = SimpleDocument(data=1)
        d.document_save()
        d = SimpleDocument.objects.get(data=1)
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, d.id)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())

    def test_document_save_1(self):
        d = SimpleDocument(data=1, document_id=123, id=17)
        self.assertRaises(Document.ChangedAlready, d.document_save)

    def test_document_save_2(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.data = 2
        d.document_save()
        self.assertEqual(
                SimpleDocument.objects.filter(document_id=123).count(), 2)
        d = SimpleDocument.objects.order_by('-id')[0]
        self.assertEqual(d.data, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocument.objects.order_by('id')[0]
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_save_3(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.data = 2
        d.id = None
        d.document_save()
        self.assertEqual(
                SimpleDocument.objects.filter(document_id=123).count(), 2)
        d = SimpleDocument.objects.order_by('-id')[0]
        self.assertEqual(d.data, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocument.objects.order_by('id')[0]
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_delete(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.document_delete()
        self.assertEqual(
                SimpleDocument.objects.filter(document_id=123).count(), 1)
        d = SimpleDocument.objects.get()
        self.assertEqual(d.data, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_get_or_404(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        d = SimpleDocument.document_get_or_404(
                datetime.now(), document_id=123)
        self.assertEqual(d.data, 1)

    def test_document_get_or_404_1(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        self.assertRaises(Http404, SimpleDocument.document_get_or_404,
                datetime.now(), document_id=12)

    def test_document_get(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        d = SimpleDocument.document_get(datetime.now(), document_id=123)
        self.assertEqual(d.data, 1)

    def test_document_get_1(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        self.assertRaises(SimpleDocument.DoesNotExist,
                SimpleDocument.document_get,
                datetime.now(), document_id=12)

    def test_at(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        id1 = d.id
        t = datetime.now()
        sleep(0.001)
        d.data = 2
        d.document_save()
        id2 = d.id
        self.assertEqual(SimpleDocument.at(t).get().id, id1)
        self.assertEqual(SimpleDocument.at(datetime.now()).get().id, id2)

    def test_history(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.data = 2
        d.document_save()
        self.assertEqual(d.history().count(), 2)
        self.assertEqual(d.history()[0].data, 2)
        self.assertEqual(d.history()[1].data, 1)

    def test_document_restore(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        t1 = datetime.now()
        sleep(0.001)
        d.data = 2
        d.document_save()
        t2 = datetime.now()
        sleep(0.001)
        self.assertEqual(SimpleDocument.at(t2).get(document_id=123).data, 2)
        self.assertEqual(SimpleDocument.at(t1).get(document_id=123).data, 1)
        SimpleDocument.at(t1).get(document_id=123).document_restore()
        self.assertEqual(
                SimpleDocument.at(datetime.now()).get(document_id=123).data, 1)
        sleep(0.001)
        SimpleDocument.at(t2).get(document_id=123).document_restore()
        self.assertEqual(
                SimpleDocument.at(datetime.now()).get(document_id=123).data, 2)


class DocumentPartFTest(TestCase):
    def tearDown(self):
        FPart.objects.all().delete()
        DocumentF.objects.all().delete()

    def test_history(self):
        p1 = FPart(partdata=1)
        p1.save()
        p2 = FPart(partdata=2)
        p2.save()
        before = datetime.now()
        sleep(0.001)
        d = DocumentF(data=1, link=p1)
        d.document_save()
        sleep(0.001)
        inter = datetime.now()
        d.link = p2
        d.document_save()
        sleep(0.001)
        after = datetime.now()
        self.assertEqual(p1.history().count(), 2)
        self.assertEqual(p1.history()[0].partdata, 2)
        self.assertEqual(p1.history()[1].partdata, 1)
        self.assertEqual(p2.history().count(), 2)
        self.assertEqual(p2.history()[0].partdata, 2)
        self.assertEqual(p2.history()[1].partdata, 1)

    def test_document_f(self):
        p1 = FPart(partdata=1)
        p1.save()
        p2 = FPart(partdata=2)
        p2.save()
        before = datetime.now()
        sleep(0.001)
        d = DocumentF(data=1, link=p1)
        d.document_save()
        sleep(0.001)
        inter = datetime.now()
        d.link = p2
        d.document_save()
        sleep(0.001)
        after = datetime.now()
        self.assertEqual(FPart.at(before).count(), 0)
        self.assertEqual(FPart.document_get(inter).partdata, 1)
        self.assertEqual(FPart.document_get(after).partdata, 2)


class DocumentPartFFTest(TestCase):
    def tearDown(self):
        FFPart0.objects.all().delete()
        FFPart.objects.all().delete()
        DocumentFF.objects.all().delete()

    def test_document_ff(self):
        p1 = FFPart0(partdata=1)
        p1.save()
        pp1 = FFPart(partlink=p1)
        pp1.save()
        d = DocumentFF(data=1, link=pp1)
        d.document_save()
        after = datetime.now()
        self.assertEqual(FFPart0.document_get(after).partdata, 1)

    def test_document_ff_1(self):
        p1 = FFPart0(partdata=1)
        p1.save()
        pp1 = FFPart(partlink=p1)
        pp1.save()
        p2 = FFPart0(partdata=2)
        p2.save()
        pp2 = FFPart(partlink=p2)
        pp2.save()
        before = datetime.now()
        sleep(0.001)
        d = DocumentFF(data=1, link=pp1)
        d.document_save()
        sleep(0.001)
        inter = datetime.now()
        d.link = pp2
        d.document_save()
        sleep(0.001)
        after = datetime.now()
        self.assertEqual(FFPart0.at(before).count(), 0)
        self.assertEqual(FFPart0.document_get(inter).partdata, 1)
        self.assertEqual(FFPart0.document_get(after).partdata, 2)


class DocumentPartBTest(TestCase):
    def tearDown(self):
        BPart.objects.all().delete()
        DocumentB.objects.all().delete()

    def test_document_b(self):
        before = datetime.now()
        sleep(0.001)
        d = DocumentB(data=1)
        d.document_save()
        p = BPart(partdata=1)
        d.bpart_set.add(p)
        sleep(0.001)
        inter = datetime.now()
        d.data = 2
        d.document_save()
        p = BPart(partdata=2)
        d.bpart_set.add(p)
        sleep(0.001)
        after = datetime.now()
        self.assertEqual(BPart.at(before).count(), 0)
        self.assertEqual(BPart.document_get(inter).partdata, 1)
        self.assertEqual(BPart.document_get(after).partdata, 2)


class DocumentPartFBTest(TestCase):
    def tearDown(self):
        FBPart0.objects.all().delete()
        FBPart.objects.all().delete()
        DocumentFB.objects.all().delete()

    def test_document_fb(self):
        pp1 = FBPart()
        pp1.save()
        p1 = FBPart0(partlink=pp1, partdata=1)
        p1.save()
        pp2 = FBPart()
        pp2.save()
        p2 = FBPart0(partlink=pp2, partdata=2)
        p2.save()
        before = datetime.now()
        sleep(0.001)
        d = DocumentFB(data=1, link=pp1)
        d.document_save()
        sleep(0.001)
        inter = datetime.now()
        d.link = pp2
        d.document_save()
        sleep(0.001)
        after = datetime.now()
        self.assertEqual(FBPart0.at(before).count(), 0)
        self.assertEqual(FBPart0.document_get(inter).partdata, 1)
        self.assertEqual(FBPart0.document_get(after).partdata, 2)


class DocumentFK(TestCase):
    def tearDown(self):
        DocumentFKSource.objects.all().delete()
        DocumentFKDestination.objects.all().delete()

    def test_document_fk(self):
        before = datetime.now()
        sleep(0.001)
        dd = DocumentFKDestination(data=1)
        dd.document_save()
        sleep(0.001)
        inter = datetime.now()
        dd.data = 2
        dd.document_save()
        sleep(0.001)
        after = datetime.now()
        ds = DocumentFKSource()
        ds.link = dd.document_id
        ds.document_save()
        ds = DocumentFKSource.objects.get(pk=1)
        self.assertRaises(DocumentFKDestination.DoesNotExist,
                DocumentFKDestination.at(before).get)
        self.assertEqual(DocumentFKDestination.at(inter).get(
            document_id=ds.link).data, 1)
        self.assertEqual(DocumentFKDestination.at(after).get(
            document_id=ds.link).data, 2)


class SimpleDocumentChildTest(TestCase):
    def tearDown(self):
        SimpleDocument.objects.all().delete()
        SimpleDocumentChild.objects.all().delete()

    def test_document_save_0(self):
        d = SimpleDocumentChild(data=1, cdata=11)
        d.document_save()
        d = SimpleDocumentChild.objects.get(data=1)
        self.assertEqual(d.cdata, 11)
        sleep(0.001)
        d.cdata = 111
        d.document_save()
        d = SimpleDocumentChild.document_get(datetime.now(), data=1)
        self.assertEqual(d.cdata, 111)

    def test_document_save(self):
        d = SimpleDocumentChild(data=1000, cdata=1)
        d.document_save()
        d = SimpleDocumentChild.objects.get(cdata=1)
        self.assertEqual(d.cdata, 1)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())

    def test_document_save_1(self):
        d = SimpleDocumentChild(data=1000, cdata=1,
                document_id=123, id=17)
        self.assertRaises(Document.ChangedAlready, d.document_save)

    def test_document_save_2(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.cdata = 2
        d.document_save()
        self.assertEqual(
                SimpleDocumentChild.objects.filter(document_id=123).count(), 2)
        d = SimpleDocumentChild.objects.order_by('-id')[0]
        self.assertEqual(d.cdata, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocumentChild.objects.order_by('id')[0]
        self.assertEqual(d.cdata, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_save_3(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.cdata = 2
        d.id = None
        d.document_save()
        self.assertEqual(
                SimpleDocumentChild.objects.filter(document_id=123).count(), 2)
        d = SimpleDocumentChild.objects.order_by('-id')[0]
        self.assertEqual(d.cdata, 2)
        self.assertEqual(d.document_id, 123)
        self.assertEqual(d.document_end, datetime.max)
        self.assertTrue(d.document_start <= datetime.now())
        d = SimpleDocumentChild.objects.order_by('id')[0]
        self.assertEqual(d.cdata, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_delete(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        t = datetime.now()
        d.document_delete()
        self.assertEqual(
                SimpleDocumentChild.objects.filter(document_id=123).count(), 1)
        d = SimpleDocumentChild.objects.get()
        self.assertEqual(d.cdata, 1)
        self.assertEqual(d.document_id, 123)
        self.assertTrue(d.document_end <= datetime.now())
        self.assertTrue(d.document_start <= t)

    def test_document_get_or_404(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        d = SimpleDocumentChild.document_get_or_404(
                datetime.now(), document_id=123)
        self.assertEqual(d.cdata, 1)

    def test_document_get_or_404_1(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        self.assertRaises(Http404, SimpleDocumentChild.document_get_or_404,
                datetime.now(), document_id=12)

    def test_document_get(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        d = SimpleDocumentChild.document_get(
                datetime.now(), document_id=123)
        self.assertEqual(d.cdata, 1)

    def test_document_get_1(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        self.assertRaises(SimpleDocumentChild.DoesNotExist,
                SimpleDocumentChild.document_get,
                datetime.now(), document_id=12)

    def test_at(self):
        d = SimpleDocumentChild(data=1000, cdata=1, document_id=123)
        d.document_save()
        id1 = d.id
        t = datetime.now()
        sleep(0.001)
        d.cdata = 2
        d.document_save()
        id2 = d.id
        self.assertNotEqual(id1, id2)
        self.assertEqual(SimpleDocumentChild.at(t).get().id, id1)
        self.assertEqual(
                SimpleDocumentChild.at(datetime.now()).get().id, id2)


class TestNow(TestCase):
    def test_now(self):
        t1 = now()
        sleep(0.001)
        t2 = now()
        self.assertEqual(t1, t2)
        set_now()
        t2 = now()
        self.assertFalse(t1 == t2)


class TestNowManager(TestCase):
    def tearDown(self):
        SimpleDocument.objects.all().delete()

    def test_manager(self):
        d = SimpleDocument(data=1, document_id=123)
        d.document_save()
        id1 = d.id
        t = datetime.now()
        sleep(0.001)
        d.data = 2
        d.document_save()
        id2 = d.id
        set_now()
        self.assertEqual(SimpleDocument.now.get().id, id2)
        set_now(t)
        self.assertEqual(SimpleDocument.now.get().id, id1)


class Test_save_now(TestCase):
    def tearDown(self):
        SimpleDocument.objects.all().delete()

    def test_save_now(self):
        d = SimpleDocument(data=1, document_id=123)
        d.save_now()
        id1 = d.id
        sleep(0.001)
        d.data = 2
        d.save_now()
        id2 = d.id
        self.assertEqual(SimpleDocument.now.get().id, id2)

