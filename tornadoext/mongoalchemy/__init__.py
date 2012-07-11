# coding: utf-8

from __future__ import absolute_import

from math import ceil
from mongoalchemy import document, exceptions, fields, session, query
from tornado.web import HTTPError

from tornadoext.mongoalchemy.meta import make_document_class


def _include_mongoalchemy(obj):
    #for key in dir(fields):
    #    if not hasattr(obj, key):
    #        setattr(obj, key, getattr(fields, key))
    #        

    # changes 
    any(setattr(obj, key, getattr(fields, key))
            for key in dir(fields) if not hasattr(obj, key))
    key = 'DocumentField'
    setattr(obj, key, getattr(document, key))


def _get_mongo_uri(app):
    app.settings.setdefault('MONGOALCHEMY_SERVER', 'localhost')
    app.settings.setdefault('MONGOALCHEMY_PORT', '27017')
    app.settings.setdefault('MONGOALCHEMY_USER', None)
    app.settings.setdefault('MONGOALCHEMY_PASSWORD', None)
    app.settings.setdefault('MONGOALCHEMY_OPTIONS', None)

    auth = ''
    database = ''

    if app.settings.get('MONGOALCHEMY_USER') is not None:
        auth = app.settings.get('MONGOALCHEMY_USER')
        if app.settings.get('MONGOALCHEMY_PASSWORD') is not None:
            auth = '%s:%s' % (auth, app.settings.get('MONGOALCHEMY_PASSWORD'))
        auth += '@'

        if not app.settings.get('MONGOALCHEMY_SERVER_AUTH', True):
            database = app.settings.get('MONGOALCHEMY_DATABASE')

    options = ''

    if app.settings.get('MONGOALCHEMY_OPTIONS') is not None:
        options = "?%s" % app.settings.get('MONGOALCHEMY_OPTIONS')

    uri = 'mongodb://%s%s:%s/%s%s' % (auth, app.settings.get('MONGOALCHEMY_SERVER'),
                                   app.settings.get('MONGOALCHEMY_PORT'), database, options)

    return uri


class ImproperlyConfiguredError(Exception):
    """Exception for error on settingsurations."""
    pass


class _QueryField(object):

    def __init__(self, db):
        self.db = db

    def __get__(self, obj, cls):
        try:
            return cls.query_class(cls, self.db.session)
        except Exception, e:
            return None


class MongoAlchemy(object):
    """Class used to control the MongoAlchemy integration to a Flask application.

    You can use this by providing the Flask app on instantiation or by calling an :meth:`init_app` method
    an instance object of `MongoAlchemy`. Here a sample of providing the application on instantiation: ::

        app = Application()
        db = MongoAlchemy(app)

    And here calling the :meth:`init_app` method: ::

        db = MongoAlchemy()

        def init_app():
            app = Application(__name__)
            db.init_app(app)
            return app
    """

    def __init__(self, app=None):
        self.Document = make_document_class(self, Document)
        self.Document.query = _QueryField(self)

        _include_mongoalchemy(self)

        if app is not None:
            self.init_app(app)
        else:
            self.session = None

    def init_app(self, app):
        """This callback can be used to initialize an application for the use with this
        MongoDB setup. Never use a database in the context of an application not
        initialized that way or connections will leak."""
        if 'MONGOALCHEMY_DATABASE' not in app.settings:
            raise ImproperlyConfiguredError("You should provide a database name (the MONGOALCHEMY_DATABASE setting).")

        uri = _get_mongo_uri(app)
        self.session = session.Session.connect(app.settings.get('MONGOALCHEMY_DATABASE'),
                                               safe=app.settings.get('MONGOALCHEMY_SAFE_SESSION', False),
                                               host=uri,
                                               )
        self.Document._session = self.session
        # Document direct use reverse_url
        self.Document.reverse_url = app.reverse_url


class Pagination(object):
    """Internal helper class returned by :meth:`~BaseQuery.paginate`."""

    def __init__(self, query, page, per_page, total, items):
        #: query object used to create this
        #: pagination object.
        self.query = query
        #: current page number
        self.page = page
        #: number of items to be displayed per page
        self.per_page = per_page
        #: total number of items matching the query
        self.total = total
        #: list of items for the current page
        self.items = items

    @property
    def pages(self):
        """The total number of pages"""
        return int(ceil(self.total / float(self.per_page)))

    @property
    def next_num(self):
        """The next page number."""
        return self.page + 1

    def has_next(self):
        """Returns ``True`` if a next page exists."""
        return self.page < self.pages

    def next(self, error_out=False):
        """Return a :class:`Pagination` object for the next page."""
        return self.query.paginate(self.page + 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """The previous page number."""
        return self.page - 1

    def has_prev(self):
        """Returns ``True`` if a previous page exists."""
        return self.page > 1

    def prev(self, error_out=False):
        """Return a :class:`Pagination` object for the previous page."""
        return self.query.paginate(self.page - 1, self.per_page, error_out)


class BaseQuery(query.Query):
    """Base class for custom user query classes.

    This class provides some methods and can be extended to provide a customized query class to a user document.

    Here an example: ::

        from flaskext.mongoalchemy import BaseQuery
        from application import db

        class MyCustomizedQuery(BaseQuery):

            def get_johns(self):
                return self.filter(self.type.first_name == 'John')

        class Person(db.Document):
            query_class = MyCustomizedQuery
            name = db.StringField()

    And you will be able to query the Person model this way: ::

        >>> johns = Person.query.get_johns().first()

    *Note:* If you are extending BaseQuery and writing an ``__init__`` method,
    you should **always** call this class __init__ via ``super`` keyword.

    Here an example: ::

        class MyQuery(BaseQuery):

            def __init__(self, *args, **kwargs):
                super(MyQuery, self).__init__(*args, **kwargs)

    This class is instantiated automatically by tornado-MongoAlchemy, don't provide anything new to your ``__init__`` method."""

    def __init__(self, type, session):
        super(BaseQuery, self).__init__(type, session)

    def get(self, mongo_id):
        """Returns a :class:`Document` instance from its ``mongo_id`` or ``None``
        if not found"""
        try:
            return self.filter(self.type.mongo_id == mongo_id).first()
        except exceptions.BadValueException:
            return None

    def get_or_404(self, mongo_id):
        """Like :meth:`get` method but aborts with 404 if not found instead of
        returning `None`"""
        document = self.get(mongo_id)
        if document is None:
            raise HTTPError(404)
        return document

    def first_or_404(self):
        """Returns the first result of this query, or aborts with 404 if the result
        doesn't contain any row"""
        document = self.first()
        if document is None:
            raise HTTPError(404)
        return document

    def paginate(self, page, per_page=20, error_out=True):
        """Returns ``per_page`` items from page ``page`` By default, it will
        abort with 404 if no items were found and the page was larger than 1.
        This behaviour can be disabled by setting ``error_out`` to ``False``.

        Returns a :class:`Pagination` object."""
        if page < 1 and error_out:
            raise HTTPError(404)

        items = self.skip((page - 1) * per_page).limit(per_page).all()

        if len(items) < 1 and page != 1 and error_out:
            raise HTTPError(404)

        return Pagination(self, page, per_page, self.count(), items)


class Document(document.Document):
    "Base class for custom user documents."

    #: the query class used. The :attr:`query` attribute is an instance
    #: of this class. By default :class:`BaseQuery` is used.
    query_class = BaseQuery

    #: an instance of :attr:`query_class`. Used to query the database
    #: for instances of this document.
    query = None

    def save(self, safe=None):
        """Saves the document itself in the database.

        The optional ``safe`` argument is a boolean that specifies if the
        remove method should wait for the operation to complete.
        """
        self._session.insert(self, safe=safe)
        self._session.flush()


    def remove(self, safe=None):
        """Removes the document itself from database.

        The optional ``safe`` argument is a boolean that specifies if the
        remove method should wait for the operation to complete.
        """
        self._session.remove(self, safe=None)
        self._session.flush()

    def __cmp__(self, other):
        if isinstance(other, type(self)) and self.has_id() and other.has_id():
            return self.mongo_id.__cmp__(other.mongo_id)
        else:
            return -1

    #### addtional #####
    @property
    def pk(self):
        # FIXME maybe bug here
        if self.has_id():
            return str(self.mongo_id)

    @property
    def urn(self):
        if self.has_id():
            return 'urn:%s:%s' % (self.get_collection_name(),
                    str(self.mongo_id))

    def maybe_save(self, safe=None):
        ''' The same as save but maybe raise 400 error
        '''
        try:
            self.save()
        except (exceptions.BadValueException,
                exceptions.MissingValueException,
                exceptions.ExtraValueException), e:
            raise HTTPError(400)

    def populate(self, data):
        any(setattr(self, k, v) for k, v in data.items())

    def to_dict(self, *include):
        raw_data = self.wrap()
        data = {}
        # cut
        if include:
            any(data.update({e: raw_data[e]}) for e in include if e in raw_data)
        else:
            data = raw_data.copy()
            if '_id' in data: del data['_id']

        # virtual properties
        all_attrs = dir(self)
        any(data.update({e: getattr(self, e)}) for e in
                set(include) - set(raw_data) if e in all_attrs)

        # addtional 
        data['id'] = self.urn

        return data
