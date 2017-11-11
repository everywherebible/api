import sys, os, re
from collections import OrderedDict, defaultdict
from copy import deepcopy
from os.path import dirname, join
from shutil import rmtree
import tempfile
from zipfile import ZipFile

from ..xml_generator import XmlGenerator, strs
from .. import mkdirs

BOOKS = OrderedDict([
  ['GEN', 'Genesis'],
  ['EXO', 'Exodus'],
  ['LEV', 'Leviticus'],
  ['NUM', 'Numbers'],
  ['DEU', 'Deuteronomy'],
  ['JOS', 'Joshua'],
  ['JDG', 'Judges'],
  ['RUT', 'Ruth'],
  ['1SA', '1 Samuel'],
  ['2SA', '2 Samuel'],
  ['1KI', '1 Kings'],
  ['2KI', '2 Kings'],
  ['1CH', '1 Chronicles'],
  ['2CH', '2 Chronicles'],
  ['EZR', 'Ezra'],
  ['NEH', 'Nehemiah'],
  ['EST', 'Esther'],
  ['JOB', 'Job'],
  ['PSA', 'Psalms'],
  ['PRO', 'Proverbs'],
  ['ECC', 'Ecclesiastes'],
  ['SNG', 'Song of Solomon'],
  ['ISA', 'Isaiah'],
  ['JER', 'Jeremiah'],
  ['LAM', 'Lamentations'],
  ['EZK', 'Ezekiel'],
  ['DAN', 'Daniel'],
  ['HOS', 'Hosea'],
  ['JOL', 'Joel'],
  ['AMO', 'Amos'],
  ['OBA', 'Obadiah'],
  ['JON', 'Jonah'],
  ['MIC', 'Micah'],
  ['NAM', 'Nahum'],
  ['HAB', 'Habakkuk'],
  ['ZEP', 'Zephaniah'],
  ['HAG', 'Haggai'],
  ['ZEC', 'Zechariah'],
  ['MAL', 'Malachi'],
  ['MAT', 'Matthew'],
  ['MRK', 'Mark'],
  ['LUK', 'Luke'],
  ['JHN', 'John'],
  ['ACT', 'Acts'],
  ['ROM', 'Romans'],
  ['1CO', '1 Corinthians'],
  ['2CO', '2 Corinthians'],
  ['GAL', 'Galatians'],
  ['EPH', 'Ephesians'],
  ['PHP', 'Philippians'],
  ['COL', 'Colossians'],
  ['1TH', '1 Thessalonians'],
  ['2TH', '2 Thessalonians'],
  ['1TI', '1 Timothy'],
  ['2TI', '2 Timothy'],
  ['TIT', 'Titus'],
  ['PHM', 'Philemon'],
  ['HEB', 'Hebrews'],
  ['JAS', 'James'],
  ['1PE', '1 Peter'],
  ['2PE', '2 Peter'],
  ['1JN', '1 John'],
  ['2JN', '2 John'],
  ['3JN', '3 John'],
  ['JUD', 'Jude'],
  ['REV', 'Revelation'],
])


BOOK_RE = re.compile(r'^([A-Z0-9]{3})(\d{1,3})\.htm$')
VERSE_ID_RE = re.compile(r'^V(\d+)')
LEADING_P_RE = re.compile('^\xc2\s*')

def chapters(files):
    matches = (BOOK_RE.match(f) for f in files if BOOK_RE.match(f))
    book_chapter_filenames = ((m.groups()[0], int(m.groups()[1]), m.string)
        for m in matches)
    return (f for (b, c, f) in book_chapter_filenames if c > 0 and b in BOOKS)


def chapter_counts(chapters):
    chapters_by_book = defaultdict(lambda: [])
    for c in chapters:
        match = BOOK_RE.match(c)
        book, chapter = match.groups()
        chapters_by_book[book] += [int(chapter)]
    return OrderedDict((BOOKS[b], len(chapters_by_book[b])) for b in BOOKS)


def parts(fname):
    match = BOOK_RE.match(fname)
    if not match:
        raise Exception('unknown filename: ' + fname)
    book_abbrev = match.groups()[0]
    return {
        'fname': fname,
        'book_abbrev': book_abbrev,
        'book': BOOKS[book_abbrev],
        'book_index': BOOKS.keys().index(book_abbrev),
        'chapter': int(match.groups()[1])
    }


def with_chapter_meta(fname, g):
    for type, val in g:
        yield (type, val, parts(fname))


def with_stack(g):
    stack = []
    for type, val, meta in g:
        if type == 'start':
            stack.append(val)

        yield (type, val, meta, stack[:])

        if type == 'end':
            assert stack[-1]['tag'] == val['tag']
            stack.pop()


def only_body(g):
    in_body = False
    for type, val, meta, stack in g:
        if type == 'start' and val['tag'] == 'body':
            in_body = True
        elif type == 'end' and val['tag'] == 'body':
            in_body = False
        elif in_body:
            yield (type, val, meta, stack)


def strip_by_class(classname, g):
    in_tag = False
    for type, val, meta, stack in g:
        if type == 'start' and val['attrs'].get('class') == classname:
            in_tag = True
        elif type == 'end' and stack[-1]['attrs'].get('class') == classname:
            in_tag = False
        elif not in_tag:
            yield (type, val, meta, stack)


def class_to_tag(classname, tag, g):
    for type, val, meta, stack in g:
        if type == 'start' and val['tag'] == 'div' and \
                val['attrs'].get('class') == classname:
            val = deepcopy(val)
            val['tag'] = tag
            del val['attrs']['class']
        elif type == 'end' and val['tag'] == 'div' and \
                stack[-1]['attrs'].get('class') == classname:
            val = dict(val)
            val['tag'] = tag
        yield (type, val, meta, stack)


def class_p_to_p(g):
    for type, val, meta, stack in g:
        if type == 'start' and val['tag'] == 'div' and \
                val['attrs'].get('class') == 'p':
            val = deepcopy(val)
            val['tag'] = u'p'
            del val['attrs']['class']
        elif type == 'end' and val['tag'] == 'div' and \
                stack[-1]['attrs'].get('class') == 'p':
            val = dict(val)
            val['tag'] = u'p'
        yield (type, val, meta, stack)


def translate_class(from_, to, g):
    for type, val, meta, stack in g:
        if type == 'start' and val['attrs'].get('class') == from_:
            val['attrs']['class'] = to
        yield (type, val, meta, stack)


def translate_verse_ids(g):
    id_map = {}
    for type, val, meta, stack in g:
        if type == 'start':
            match = VERSE_ID_RE.match(val['attrs'].get('id', ''))
            if match:
                new_id = 'v%02d%03d%003d-1' % (
                        meta['book_index'] + 1,
                        meta['chapter'],
                        int(match.groups()[0]))
                id_map[val['attrs']['id']] = new_id
                val['attrs']['id'] = new_id
            if VERSE_ID_RE.match(val['attrs'].get('href', '')[1:]):
                val['attrs']['href'] = '#' + id_map[val['attrs']['href'][1:]]
        yield (type, val, meta, stack)


def add_chapter_header(g):
    for type, val, meta, stack in g:
        yield (type, val, meta, stack)
        if type == 'start' and val['attrs'].get('class') == 'kjv':
            new_val = {'tag': 'h2', 'attrs': {}}
            new_stack = stack + [new_val]
            text = u'%s %d' % (meta['book'], meta['chapter'])
            yield ('start', new_val, meta, new_stack)
            yield ('text', text, meta, new_stack)
            yield ('end', {'tag': 'h2', 'attrs': {}}, meta, new_stack)


def wrap_verse_with_span(g):
    new_verse_tag = None
    for type, val, meta, stack in g:
        if type == 'start' and val['attrs'].get('class') == 'verse-num':
            if new_verse_tag:
                yield ('end', {'tag': 'span', 'attrs': {}}, meta, stack + [new_verse_tag])
                new_verse_tag = None
            new_verse_tag = {
                'tag': 'span',
                'attrs': {
                    'class': 'verse',
                    'id': 'vt' + val['attrs']['id'][1:],
                },
            }
            new_stack = stack + [new_verse_tag]
            yield ('start', new_verse_tag, meta, new_stack)
        if type == 'end' and \
                (val['tag'] == 'p' or val['tag'] == 'blockquote') and \
                new_verse_tag:
            yield ('end', {'tag': 'span', 'attrs': {}}, meta, stack + [new_verse_tag])
            new_verse_tag = None
        yield (type, val, meta, stack)


def text_transform(transform, g):
    for type, val, meta, stack in g:
        if type == 'text':
            val = transform(val)
        yield (type, val, meta, stack)


def transform(fname, g):
    return wrap_verse_with_span(
            add_chapter_header(
                translate_verse_ids(
                    translate_class('main', 'kjv',
                        translate_class('verse', 'verse-num',
                            translate_class('notemark', 'footnote',
                                translate_class('footnote', 'footnotes',
                                    class_to_tag('p', 'p',
                                        class_to_tag('q', 'blockquote',
                                            strip_by_class('chapterlabel',
                                                strip_by_class('copyright',
                                                    strip_by_class('tnav',
                                                        strip_by_class('popup',
                                                            text_transform(lambda s: LEADING_P_RE.sub('', s),
                                                                only_body(
                                                                    with_stack(
                                                                        with_chapter_meta(fname, g)))))))))))))))))


def generate(outdir):
    thisdir = dirname(sys.modules[__name__].__file__)
    datadir = join(thisdir, '../data')
    tmpdir = tempfile.mkdtemp()
    ZipFile(join(datadir, 'eng-kjv_html.zip'), 'r').extractall(path=tmpdir)
    for fname in chapters(os.listdir(tmpdir)):
        p = parts(fname)
        fileoutdir = join(outdir, p['book'].lower().replace(' ', '-'))
        mkdirs.mkdirs(fileoutdir)
        outfile = join(fileoutdir, str(p['chapter']) + '.html')
        with open(join(tmpdir, fname)) as f:
            with open(outfile, 'w') as outf:
                for s in strs(transform(fname, XmlGenerator(f))):
                    outf.write(s.encode('utf-8'))
    rmtree(tmpdir)
