import os
import re
from shutil import rmtree
import sys
import tempfile
import unittest
from xml.dom import minidom
from zipfile import ZipFile

from generate import BOOK_RE, BOOKS, chapter_counts, chapters, transform
from ..xml_generator import XmlGenerator, strs


ACTUAL_COUNTS = {'Genesis': 50, 'Exodus': 40, 'Leviticus': 27,
        'Numbers': 36, 'Deuteronomy': 34, 'Joshua': 24, 'Judges': 21,
        'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24, '1 Kings': 22,
        '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36, 'Ezra': 10,
        'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalms': 150, 'Proverbs':
        31, 'Ecclesiastes': 12, 'Song of Solomon': 8, 'Isaiah': 66,
        'Jeremiah': 52, 'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12,
        'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4,
        'Micah': 7, 'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2,
        'Zechariah': 14, 'Malachi': 4, 'Matthew': 28, 'Mark': 16, 'Luke':
        24, 'John': 21, 'Acts': 28, 'Romans': 16, '1 Corinthians': 16,
        '2 Corinthians': 13, 'Galatians': 6, 'Ephesians': 6,
        'Philippians': 4, 'Colossians': 4, '1 Thessalonians': 5,
        '2 Thessalonians': 3, '1 Timothy': 6, '2 Timothy': 4, 'Titus': 3,
        'Philemon': 1, 'Hebrews': 13, 'James': 5, '1 Peter': 5,
        '2 Peter': 3, '1 John': 5, '2 John': 1, '3 John': 1, 'Jude': 1,
        'Revelation': 22}

class TestGenerate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        thisdir = os.path.dirname(sys.modules[__name__].__file__)
        datadir = os.path.join(thisdir, '../data')
        cls.datadir = tempfile.mkdtemp()
        zipfile = os.path.join(datadir, 'eng-kjv_html.zip')
        ZipFile(zipfile, 'r').extractall(path=cls.datadir)

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.datadir)

    def files(self):
        return os.listdir(self.datadir)

    def test_number_of_books(self):
        self.assertEqual(len(BOOKS), 66)

    def test_chapter_counts(self):
        for b, c in chapter_counts(chapters(self.files())).items():
            self.assertEqual(ACTUAL_COUNTS[b], c, 'wrong count for ' + b)

    def test_chapter_filenames(self):
        counts = chapter_counts(chapters(self.files()))
        for c in chapters(self.files()):
            m = BOOK_RE.match(c)
            book, chapter = m.groups()[0], int(m.groups()[1])
            if chapter < 1 or chapter > counts[BOOKS[book]]:
                raise Error('unexpected: ' + c)

    def test_number_of_chapters(self):
        self.assertEqual(len(list(chapters(self.files()))), 1189)

    def test_parsing_input_data(self):
        for fname in chapters(self.files()):
            with open(os.path.join(self.datadir, fname)) as f:
                for event in XmlGenerator(f):
                    assert event is not None

    def test_parsing_output_data(self):
        for fname in chapters(self.files()):
            with open(os.path.join(self.datadir, fname)) as f:
                g = strs(transform(fname, XmlGenerator(f)))
                s = re.compile(r'\s+').sub(' ', ''.join(g))
                doc = '<!DOCTYPE html><html><body>%s</body></html>' % s
                f.seek(0)
                try:
                    assert len(doc) >= 0.3 * len(f.read())
                    assert len(doc) > 500
                    minidom.parseString(doc.encode('utf-8'))
                except Exception as e:
                    print 'ERROR',fname
                    open('/tmp/err.html', 'w').write(doc.encode('utf-8'))
                    try:
                        parsed = minidom.parseString(doc.encode('utf-8'))
                        open('/tmp/err-pretty.html', 'w').write(
                                parsed.toprettyxml(indent='  ').encode('utf-8'))
                    except:
                        pass
                    raise e

if __name__ == '__main__':
    unittest.main()
