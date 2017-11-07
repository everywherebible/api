try:
    from html import escape  # python 3.x
except ImportError:
    from cgi import escape  # python 2.x
from xml.parsers import expat


class XmlGenerator(object):
  def __init__(self, source, encoding=None):
    if isinstance(source, unicode) and encoding:
      self._source = source.encode(encoding)
    else:
      self._source = source
    self._events = None
    self._in_cdata = False
    self._parser = expat.ParserCreate(encoding)
    self._parser.StartElementHandler = self._start
    self._parser.EndElementHandler = self._end
    self._parser.CommentHandler = self._comment
    self._parser.CharacterDataHandler = self._cdata
    self._parser.StartCdataSectionHandler = self._start_cdata
    self._parser.EndCdataSectionHandler = self._end_cdata
    self._parser.XmlDeclHandler = self._xml_decl

  def _append_to_last_event(self, data):
    self._events[-1] = (self._events[-1][0], self._events[-1][1] + data)

  def _start(self, tag, attrs_):
    self._events.append(('start', {'tag': tag, 'attrs': attrs_}))

  def _end(self, tag):
    self._events.append(('end', {'tag': tag}))

  def _comment(self, data):
    self._events.append(('comment', {'text': data}))

  def _cdata(self, data):
    event = 'cdata' if self._in_cdata else 'text'
    if self._events[-1][0] == event:
      self._append_to_last_event(data)
    else:
      self._events.append((event, data))

  def _start_cdata(self):
    self._in_cdata = True

  def _end_cdata(self):
    self._in_cdata = False

  def _xml_decl(self, version, encoding, standalone):
    self._events.append(('xml-declaration', {
        'version': version,
        'encoding': encoding,
        'standalone': standalone,
    }))

  def next(self):
    if self._events is None:
      self._events = []
      if hasattr(self._source, 'read'):
          self._parser.ParseFile(self._source)
      else:
          self._parser.Parse(self._source, 0)
    try:
      return self._events.pop(0)
    except IndexError:
      raise StopIteration

  def __iter__(self):
    return self

def strs(g):
    for item in g:
        type = item[0]
        val = item[1]
        if type == 'start':
            yield '<'
            yield val['tag']
            for k, v in val['attrs'].items():
                yield ' '
                yield k
                yield '="'
                yield v
                yield '"'
            yield '>'
        elif type == 'end':
            yield '</'
            yield val['tag']
            yield '>'
        elif type == 'text':
            yield escape(val)
