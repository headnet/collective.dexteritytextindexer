"""
DefaultDexterityTextIndexFieldConverter    the default field converter
NamedfileFieldConverter                    an optional namedfile field
converter only enabled when plone.namedfile is installed
"""

from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError
from collective.dexteritytextindexer import interfaces
from five import grok
from plone.dexterity.interfaces import IDexterityContent
from zope.schema.interfaces import IField, IInt
from z3c.form.interfaces import IWidget
import logging


try:
    from plone.namedfile.interfaces import INamedFileField
except ImportError:
    HAS_NAMEDFILE = False
else:
    HAS_NAMEDFILE = True


LOGGER = logging.getLogger('collective.dexteritytextindexer')


class DefaultDexterityTextIndexFieldConverter(grok.MultiAdapter):
    """Fallback field converter which uses the rendered widget in display
    mode for generating a indexable string.
    """

    grok.provides(interfaces.IDexterityTextIndexFieldConverter)
    grok.adapts(IDexterityContent, IField, IWidget)

    def __init__(self, context, field, widget):
        """Initialize field converter"""
        self.context = context
        self.field = field
        self.widget = widget

    def convert(self):
        """Convert the adapted field value to text/plain for indexing"""
        try:
            html = self.widget.render().strip().encode('utf-8')
            transforms = getToolByName(self.context, 'portal_transforms')
            stream = transforms.convertTo('text/plain', html, mimetype='text/html')
            return stream.getData().strip()
        except (ConflictError, KeyboardInterrupt):
            raise

        except Exception, e:
            LOGGER.error('Error while trying to convert file contents '
                         'to "text/plain": %s' % str(e))


if HAS_NAMEDFILE:
    class NamedfileFieldConverter(DefaultDexterityTextIndexFieldConverter):
        """Converts the file data of a named file using portal_transforms.
        """

        grok.provides(interfaces.IDexterityTextIndexFieldConverter)
        grok.adapts(IDexterityContent, INamedFileField, IWidget)

        def convert(self):
            """Transforms file data to text for indexing safely.
            """
            storage = self.field.interface(self.context)
            data = self.field.get(storage)

            # if there is no data, do nothing
            if not data or data.getSize() == 0:
                return ''

            # if there is no path to text/plain, do nothing
            transforms = getToolByName(self.context, 'portal_transforms')

            # pylint: disable=W0212
            # W0212: Access to a protected member _findPath of a client class
            if not transforms._findPath(data.contentType, 'text/plain'):
                return ''
            # pylint: enable=W0212

            # convert it to text/plain
            try:
                datastream = transforms.convertTo(
                    'text/plain', data.data, mimetype=data.contentType,
                    filename=data.filename)
                return datastream.getData()

            except (ConflictError, KeyboardInterrupt):
                raise

            except Exception, e:
                LOGGER.error('Error while trying to convert file contents '
                             'to "text/plain": %s' % str(e))


class IntFieldConverter(DefaultDexterityTextIndexFieldConverter):
    """Converts the data of a int field"""

    grok.provides(interfaces.IDexterityTextIndexFieldConverter)
    grok.adapts(IDexterityContent, IInt, IWidget)

    def convert(self):
        """return the adapted field value"""
        storage = self.field.interface(self.context)
        value = self.field.get(storage)
        return str(value)
