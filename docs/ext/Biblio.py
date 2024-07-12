import re
import string

from collections    import defaultdict
from typing         import List, Dict, Any, Tuple

from docutils               import nodes
from docutils.parsers.rst   import Directive, directives

from sphinx                 import addnodes, environment
from sphinx.directives      import ObjectDescription
from sphinx.domains         import Domain, Index, IndexEntry
from sphinx.util.docutils   import SphinxDirective
from sphinx.addnodes        import pending_xref


def int_to_roman(input):
    """ Convert an integer to a Roman numeral. """

    if not isinstance(input, type(1)):
        raise TypeError("expected integer, got %s" % type(input))
    if not 0 < input < 4000:
        raise ValueError("Argument must be between 1 and 3999")
    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return ''.join(result)

class ParseError(Exception):
    pass

class Issue:

    classes = {
        'year':         ['book-issue-year'],
        'volume':       ['book-issue-volume'],
        'fascicle':     ['book-issue-fascicle'],
        'part':         ['book-issue-part'],
        'punctuation':  ['book-issue-punctuation'],
        'title':        ['book-issue-title'],
        'language':     ['book-issue-language'],
        'series':       ['book-issue-series'],
        'filename':     ['book-issue-filename'],
        'front':        ['book-issue-front']
    }

    languages_dict = {
        'ENG' : 'English',
        'RUS' : 'Russian',
        'POL' : 'Polish',
        "DEU" : 'German'
    }

    def __init__(self
                , year:          str
                , language:      str
                , edition:       int = 1
                , series:        str = ''
                , volume:        str = ''
                , volume_name:   str = ''
                , part:          int = 0
                , part_name:     str = ''
                , fascicle:      int = 0
                , fascicle_name: str = ''
                , links:         Dict[str, str] = {}
                , front:         str = ''):
        self.year          = year
        self.language      = language
        self.edition       = edition
        self.series        = series
        self.volume        = volume
        self.volume_name   = volume_name
        self.part          = part
        self.part_name     = part_name
        self.fascicle      = fascicle
        self.fascicle_name = fascicle_name
        self.links         = links
        self.front         = front

    @classmethod
    def init_from_raw(cls, raw_source: List[str]):
        raw = {
            'year':          '',
            'language':      '',
            'edition':       '',
            'series':        '',
            'volume':        '',
            'volume_name':   '',
            'part':          '',
            'part_name':     '',
            'fascicle':      '',
            'fascicle_name': '',
            'links':         {},
            'front':         ''
        }

        lexer = {
            'year':          re.compile(r'^\:year\:\s+(\d{4})'),
            'language':      re.compile(r'^\:language\:\s+([A-Za-z]{3})'),
            'edition':       re.compile(r'^\:edition\:\s+(\d+)'),
            'series':        re.compile(r'^\:series\:\s+(.*?)$'),
            'volume':        re.compile(r'\:volume\:\s+(\w+)'),
            'volume_name':   re.compile(r'^\:volume_name\:\s+(.*?)$'),
            'part':          re.compile(r'\:part\:\s(\w+)'),
            'part_name':     re.compile(r'^\:part_name\:\s+(.*?)$'),
            'fascicle':      re.compile(r'\:fascicle\:\s(\w+)'),
            'fascicle_name': re.compile(r'^\:fascicle_name\:\s+(.*?)$'),
            'links':         re.compile(r'^\:link\s+([\w\.\-]+?)\:\s+(.*)$'),
            'front':         re.compile(r'^\:front\:\s+(.*?)$')
        }

        for line in raw_source:
            match_links = lexer['links'].match(line)
            if match_links: # not unique fields
                raw['links'][match_links.group(1)] = match_links.group(2)
            else:           # unique fields
                for field in raw:
                    match = lexer[field].match(line)
                    if match:
                        if raw[field] == '':
                            if not match.group(1) == '':
                                raw[field] = match.group(1)
                        else:
                            raise ParseError("Issue: field duplication " + field)

        if raw['part'] == '':
            raw['part'] = 0
        
        if raw['fascicle'] == '':
            raw['fascicle'] = 0

        return Issue(raw['year']
                    , raw['language']
                    , int(raw["edition"])
                    , raw['series']
                    , raw["volume"]
                    , raw["volume_name"]
                    , int(raw["part"])
                    , raw["part_name"]
                    , int(raw["fascicle"])
                    , raw["fascicle_name"]
                    , raw['links']
                    , raw['front'])

    def set_static_path(self, static_path: str):
        self.static_path = static_path

    def build_issue_title_prefix_node(self) -> nodes.Node:
        prefix_node = nodes.inline()

        if self.volume != '':
            prefix_node += nodes.inline(text=', Volume {}'.format(self.volume)
                                       , classes=self.classes['volume'])

        if self.fascicle != 0:
            prefix_node += nodes.inline(text=', Fascicle {}'.format(self.fascicle)
                                       , classes=self.classes['fascicle'])

        if self.part != 0:
            prefix_node += nodes.inline(text=', Part {}'.format(self.part)
                                       , classes=self.classes['part'])

        prefix_node += nodes.inline(text=":", classes=self.classes['punctuation'])

        return prefix_node

    def build_issue_title(self) -> str:
        issue_title = ''

        if self.part_name != '':
            issue_title = self.part_name
        elif self.fascicle_name != '':
            issue_title = self.fascicle_name
        elif self.volume_name != '':
            issue_title = self.volume_name

        return issue_title

    def build_issue_title_node(self) -> nodes.Node:
        issue_title_node = nodes.inline(text=self.build_issue_title())
        issue_title_node['classes'] = self.classes['title']

        issue_title_node += nodes.inline(text=" - ",
                                         classes=self.classes['punctuation'])

        return issue_title_node

    def build_file_component(self) -> str:
        file_component_str = '({}.{})'.format(self.year, int_to_roman(int(self.edition)))
        if self.volume != '':
            file_component_str += '.V{}'.format(self.volume)
        if self.fascicle != 0:
            file_component_str += '.F{}'.format(self.fascicle)
        if self.part != 0:
            file_component_str += '.P{}'.format(self.part)

        issue_title = self.build_issue_title()

        if not issue_title == '':
            issue_title = re.compile(r'\s').sub('_', issue_title)
            file_component_str += '.{}'.format(issue_title)

        file_component_str += '.[{}]'.format(self.language.upper())

        return file_component_str

    def build_language_node(self) -> nodes.Node:
        language_string = self.language.upper()

        if language_string in self.languages_dict:
            language_string = self.languages_dict[language_string]

        return nodes.inline(text=' ({})'.format(language_string)
                           , classes=self.classes['language'])

    def build_series_node(self, domain: 'Athenaeum' = None) -> List[nodes.Node]:
        if self.series == '':
            return []

        series_unique_id = -1 \
            if domain is None else domain.get_series_unique_id(self.series)
        domain_name = 'problematic' if domain is None else domain.name
        current_file_name = 'problematic' \
            if domain is None else domain.env.docname

        series_index_file_name = '{}-{}_{}'.format( domain_name
                                                    , 'series'
                                                    , series_unique_id)

        issue_reference = nodes.reference(internal=True)
        issue_reference['refuri'] = domain.env.app.builder.get_relative_uri( 
            current_file_name, series_index_file_name)
        issue_reference += nodes.inline( text=self.series
                                       , classes=self.classes['series'])
        
        return [ nodes.inline( text=' | ', classes=self.classes['punctuation'])
               , issue_reference]

    def build_link_node(self, link) -> nodes.Node:
        reference = nodes.reference(
            '', '', internal=False, refuri=self.links[link])
        reference += nodes.strong(link, link)
        return reference

    def build_front_node(self) -> nodes.Node:
        reference = directives.uri(self.front)
        return nodes.image(uri = reference, classes=self.classes['front'], width='200px')

    def build_node(self, domain: 'Athenaeum' = None, folder: str = '') -> nodes.Node:
        issue_node = nodes.paragraph()

        issue_node += nodes.strong(text=self.year, classes=self.classes['year'])
        issue_node += self.build_issue_title_prefix_node()
        issue_node += self.build_issue_title_node()
        issue_node += nodes.inline(text='%s edition' % (int_to_roman(int(self.edition))))
        issue_node += self.build_language_node()

        for n in self.build_series_node(domain):
            issue_node += n

        info_bullet_list = nodes.bullet_list(bullet='*')

        if len(self.links) > 0:
            link_item = nodes.list_item()
            link_par = nodes.paragraph()

            for link_name in self.links:
                link_par += self.build_link_node(link_name)
                link_par += nodes.inline(text=' ')

            link_item += link_par
            info_bullet_list += link_item

        file_name_item = nodes.list_item()
        file_name_item += nodes.paragraph( text=folder + self.build_file_component()
                                         , classes=self.classes['filename'])
        info_bullet_list += file_name_item

        issue_node += info_bullet_list

        if self.front:
            # raise Exception(self.static_path)
            root_hlist = addnodes.hlist()
            root_hlist += addnodes.hlistcol('', self.build_front_node())
            root_hlist += addnodes.hlistcol('', issue_node)
            return root_hlist

        return issue_node

class Author:

    classes = {
        'author': ['book-author']
    }

    def __init__(self
                , first_name:  str
                , last_name:   str
                , middle_name: str = ''):
        self.first_name  = first_name   # str
        self.last_name   = last_name    # str
        self.middle_name = middle_name  # str
        self.is_latin = first_name[0].lower() in string.ascii_lowercase

    @classmethod
    def init_from_raw(cls, raw: str):
        name_parts = raw.split()
        if len(name_parts) == 2:
            return cls(name_parts[0], name_parts[1])
        elif len(name_parts) == 3:
            return cls(name_parts[0], name_parts[2], name_parts[1])
        else:
            raise ParseError('Author: cannot parse raw string')

    def get_full_name(self) -> str:
        return '{}-{}{}{}'.format( 'author'
                                 , self.first_name
                                 , self.middle_name
                                 , self.last_name)

    def get_displayable_name(self) -> str:
        displayable_name = ''

        if self.is_latin:
            displayable_name = self.first_name
            if not self.middle_name == '':
                displayable_name += ' {}'.format(self.middle_name)
            displayable_name += ' {}'.format(self.last_name)
        else:
            displayable_name = '{} {}'.format(self.last_name, self.first_name)
            if not self.middle_name == '':
                displayable_name += ' {}'.format(self.middle_name)

        return displayable_name

    def build_file_component(self) -> str:
        file_component = ''

        if self.is_latin:
            file_component = self.first_name
            if not self.middle_name == '':
                file_component += '.{}'.format(self.middle_name[0])
            file_component += '.{}'.format(self.last_name)
        else:
            file_component = '{}.{}'.format(self.last_name, self.first_name[0])
            if not self.middle_name == '':
                file_component += '.{}.'.format(self.middle_name[0])
        return file_component

    def build_node(self, domain: 'Athenaeum' = None) -> nodes.Node:
        
        author_unique_id = -1 \
            if domain is None else domain.get_author_unique_id(self)
        domain_name = 'problematic' \
            if domain is None else domain.name
        current_file_name = 'problematic' \
            if domain is None else domain.env.docname
        
        author_index_file_name = '{}-{}_{}'.format( domain_name
                                                  , 'author'
                                                  , author_unique_id)

        author_reference = nodes.reference(internal=True)
        author_reference['refuri'] = \
            domain.env.app.builder.get_relative_uri( current_file_name
                                                   , author_index_file_name)
        author_title = nodes.inline(text=self.get_displayable_name())
        author_title['classes']=self.classes['author']

        author_paragraph = nodes.paragraph()
        author_reference += author_title
        author_paragraph += author_reference

        return author_paragraph


class Book:

    classes = {
        'authors': ['book-authors-title'],
        'issues': ['book-issues-title'],
    }

    def __init__(self
                , title:              str
                , authors:            List["Author"]
                , id:                 int
                , issues:             List["Issue"] = []
                , subtitle:           str = ''
                , title_localized:    str = ''
                , subtitle_localized: str = ''
                , tags:               List[str] = []
                , domain:             'Domain' = None):
        self.title              = title
        self.authors            = authors
        self.id                 = 'book-%s' % id
        self.issues             = issues
        self.subtitle           = subtitle
        self.title_localized    = title_localized
        self.subtitle_localized = subtitle_localized
        self.tags               = tags
        self.domain             = domain

    def transform_title(self) -> str:
        re_the = re.compile(r'^(The)\s(.*)$').match(self.title)
        if re_the:
            return '{},{}'.format(re_the.group(2),re_the.group(1))
        
        re_a = re.compile(r'^(A)\s(.*)$').match(self.title)
        if re_a:
            return '{},{}'.format(re_a.group(2),re_a.group(1))

        return self.title

    def build_node_authors(self) -> nodes.Node:
        authors_node = nodes.paragraph(text='Authors'
                                      , classes=self.classes['authors'])

        authors_bullet_list = nodes.bullet_list(bullet='-')
        for a in self.authors:
            author_list_item = nodes.list_item()
            author_list_item += a.build_node(domain=self.domain)
            authors_bullet_list += author_list_item

        authors_node += authors_bullet_list
        return authors_node

    def build_node_issues(self) -> nodes.Node:
        issues_node = nodes.paragraph(text='Issues', classes=self.classes['issues'])

        issues_bullet_list = nodes.bullet_list(bullet='-')
        for i in sorted(self.issues, key=lambda issue: issue.year):
            issue_list_item = nodes.list_item()
            issue_list_item += i.build_node(domain=self.domain, folder=self.build_folder_title())
            issues_bullet_list += issue_list_item

        issues_node += issues_bullet_list
        return issues_node

    def build_folder_title(self) ->str:
        authors_part = []
        for author in self.authors:
            if len(authors_part) > 2:
                break

            authors_part.append(author.build_file_component())
        
        authors_str = ','.join(authors_part)
        title_str = re.compile(r'[ :\\/]').sub('_', self.title)
        return '{}-{}'.format(authors_str, title_str)

    def build_node(self) -> nodes.Node:
        book_topic = nodes.topic(classes=['book-topic'])
        book_topic += nodes.target('', '', ids=[self.id])
        book_title = nodes.paragraph(text=self.title, classes=['book-title'])
        if not self.subtitle == '':
            book_title += nodes.inline(text=': ', classes=['book-punctuation'])
            book_title += nodes.inline(text=self.subtitle, classes=['book-subtitle'])

        book_topic += book_title

        if not self.title_localized == '':
            book_title_localized = nodes.paragraph(text=self.title_localized, classes=['book-title-localized'])

            if not self.subtitle_localized == '':
                book_title_localized += nodes.inline(text=': ', classes=['book-punctuation'])
                book_title_localized += nodes.inline(text=self.subtitle_localized, classes=['book-subtitle-localized'])

            book_topic += book_title_localized

        book_tags = nodes.paragraph(classes=['book-tags-container'])

        first_space = True
        for t in self.tags:
            if first_space:
                first_space = False
            if not first_space:
                book_tags += nodes.inline(text=' ', classes=['book-punctuation'])

            tag_unique_id = -1 \
                if self.domain is None else self.domain.get_tag_unique_id(t.strip())
            domain_name = 'problematic' if self.domain is None else self.domain.name
            current_file_name = 'problematic' \
                if self.domain is None else self.domain.env.docname

            tag_index_file_name = '{}-{}_{}'.format( domain_name
                                                   , 'tag'
                                                   , tag_unique_id)

            tag_reference = nodes.reference(internal=True)
            tag_reference['refuri'] = self.domain.env.app.builder.get_relative_uri( 
                                        current_file_name, tag_index_file_name)
            tag_reference += nodes.inline(text=t.strip(), classes=['book-tag'])
            book_tags += tag_reference
        
        book_topic += book_tags

        book_folder_component = nodes.paragraph(text=self.build_folder_title(), classes=['book-file-component'])
        book_topic += book_folder_component

        book_left_bullet_list = nodes.bullet_list(bullet='*', classes=['piska'])

        authors_list_item = nodes.list_item()
        authors_list_item += self.build_node_authors()
        book_left_bullet_list += authors_list_item

        book_right_bullet_list = nodes.bullet_list(bullet='*')

        issues_list_item = nodes.list_item()
        issues_list_item += self.build_node_issues()
        book_right_bullet_list += issues_list_item

        root_hlist = addnodes.hlist()
        root_hlist += addnodes.hlistcol('', book_left_bullet_list)
        root_hlist += addnodes.hlistcol('', book_right_bullet_list)
        book_topic += root_hlist
        
        return book_topic


class BookDirective(SphinxDirective):

    has_content = True
    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'subtitle': directives.unchanged,
        'title_localized': directives.unchanged,
        'subtitle_localized': directives.unchanged,
        'authors': directives.unchanged_required,
        'tags': directives.unchanged
    }

    def parse_authors(self) -> List["Author"]:
        author_list = []
        for author_raw in self.options.get('authors').split(','):
            author = Author.init_from_raw(author_raw)
            author_list.append(author)

        return author_list

    def parse_issues(self) -> List["Issue"]:
        raw_container = []
        collecting = False
        raw = []

        for line in self.content:
            line = line.strip()

            if line == '':
                continue

            if line == ':issue:':
                collecting = True
                if len(raw) > 0:
                    raw_container.append(raw)
                    raw = []
                continue

            if collecting:
                raw.append(line)

        if len(raw) > 0:
            raw_container.append(raw)

        issue_list = []
        for raw_list in raw_container:
            issue = Issue.init_from_raw(raw_list)
            issue.set_static_path(self.config["html_static_path"])
            issue_list.append(issue)

        return issue_list

    def run(self) -> List[nodes.Node]:
        athenaeum = self.env.get_domain('athenaeum')

        book = Book( self.arguments[0]
                   , self.parse_authors()
                   , self.env.new_serialno('book')
                   , self.parse_issues()
                   , subtitle=self.options.get('subtitle', '')
                   , title_localized=self.options.get('title_localized', '')
                   , subtitle_localized=self.options.get('subtitle_localized', '')
                   , tags=[x.strip() for x in self.options.get('tags', '').split(',')]
                   , domain=athenaeum)

        athenaeum.add_book(book)

        return [book.build_node()]

def sort_index_content(content: List[Tuple[str, List[IndexEntry]]]) -> List[Tuple[str, List[IndexEntry]]]:
    for index_key in content:
        content[index_key].sort()
    return sorted(content.items())

def build_book_description(authors: List['Author'], tags: List[str]) -> str:
    return ', '.join([a.last_name for a in authors]) + ' / ' + tags[0]

class AuthorIndex(Index):
    name = 'author'
    localname = 'Author Index'
    shortname = 'Authors'

    def generate(self, docnames=None) -> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
        content = defaultdict(list)

        for name, displayname, docname, _  in self.domain.data['authors']:
            book_counter = 0
            for book in self.domain.data['books']:
                for book_author in book[4]:
                    if name == book_author.get_full_name():
                        book_counter += 1
            
            content[displayname[0].upper()].append(
                (displayname, 0, docname, '', book_counter, '', 'Author'))
                 #name, sub-type, docname, anchor, extra, qualifier, description

        return sort_index_content(content), True

class BookIndex(Index):
    name = 'all_books'
    localname = 'Book Index'
    shortname = 'Books'

    def generate(self, docnames=None):
        content = defaultdict(list)

        for name, display_name, docname, anchor, authors, series, tags in self.domain.data['books']:
            content[display_name[0].upper()].append(( display_name
                                                , 0
                                                , docname
                                                , anchor
                                                , build_book_description(authors, tags)
                                                , ''
                                                , 'Book'))

        return sort_index_content(content), True

class SeriesIndex(Index):
    name = 'series'
    localname = 'Series Index'
    shortname = 'Series'

    def generate(self, docnames=None):
        content = defaultdict(list)

        for _, display_name, docname, _ in self.domain.data['series']:
            book_counter = 0
            for book in self.domain.data['books']:
                if display_name in book[5]:
                    book_counter += 1

            content[display_name[0].upper()].append(
                (display_name, 0, docname, '', book_counter, '', 'Series'))

        return sort_index_content(content), True

class TagsIndex(Index):
    name = 'tags'
    localname = 'Tags Index'
    shortname = 'Tags'

    def generate(self, docnames=None):
        content = defaultdict(list)

        for name, display_name, docname, _ in self.domain.data['tags']:
            book_counter = 0
            for book in self.domain.data['books']:
                if display_name in book[6]:
                    book_counter += 1
            content[display_name[0].upper()].append(
                (display_name, 0, docname, '', book_counter, '', 'Tag'))

        return sort_index_content(content), True

def author_book_generator(self, docnames=None)-> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
    content = defaultdict(list)

    for _, dispname, docname, anchor, authors, _, tags in self.domain.data['books']:
        found = next((a for a in authors \
            if a.get_full_name() == self.magic_author.get_full_name()), False)

        if found:
            content[dispname[0].upper()].append(( dispname
                                                , 0
                                                , docname
                                                , anchor
                                                , build_book_description(authors, tags)
                                                , ''
                                                , 'Book'))

    return sort_index_content(content), True

def series_book_generator(self, docnames=None)-> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
    content = defaultdict(list)

    for _, dispname, docname, anchor, authors, series, tags in self.domain.data['books']:
        if self.magic_series in series:
            content[dispname[0].upper()].append(( dispname
                                                , 0
                                                , docname
                                                , anchor
                                                , build_book_description(authors, tags)
                                                , ''
                                                , 'Book'))

    return sort_index_content(content), True

def tags_book_generator(self, docnames=None)-> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
    content = defaultdict(list)

    for _, display_name, docname, anchor, authors, _, tags in self.domain.data['books']:

        if self.magic_tag in tags:
            content[display_name[0].upper()].append(( display_name
                                                    , 0
                                                    , docname
                                                    , anchor
                                                    , build_book_description(authors, tags)
                                                    , ''
                                                    , 'Book'))

    return sort_index_content(content), True

class Athenaeum(Domain):
    name = 'athenaeum'
    label = 'Athenaeum of useful books'
    roles = {}
    directives = {
        'book' : BookDirective
    }
    indices = [
        AuthorIndex,
        BookIndex,
        SeriesIndex,
        TagsIndex
    ]
    initial_data = {
        'books': [],
        'authors': [],
        'series': [],
        'tags': []
    }


    def resolve_any_xref(self, env: "BuildEnvironment", fromdocname: str, builder: "Builder", target: str, node: pending_xref, contnode: nodes.Element) -> List[Tuple[str, nodes.Element]]:
        return super().resolve_any_xref(env, fromdocname, builder, target, node, contnode)

    def get_full_qualified_name(self, node: nodes.Element) -> str:
        try:
            book_title = node.arguments[0].strip().replace(' ', '')
        except:
            book_title = "what-ta-fuck"
        return '{}-{}'.format(self.name, book_title)

    def add_author_record(self, record: Tuple[str, str, str, int]) -> None:
        self.data['authors'].append(record)

    def get_author_record(self, author: 'Author') -> Tuple[str, str, str, int]:
        return next((x for x in self.data['authors'] if x[0] == author.get_full_name()), None)

    def create_author_unique_id(self) -> int:
        return len(self.data['authors'])

    def get_author_unique_id(self, author: "Author") -> int:
        record = self.get_author_record(author)
        if record is not None:
            return record[3]
        else:
            return self.create_author_unique_id()

    def add_author(self, author: "Author") -> None:
        record = self.get_author_record(author)

        if record is None:
            author_id = self.create_author_unique_id()
            index_name = '{}_{}'.format('author', author_id)
            author_generator = type('author_index_generator_%s' % author_id
                                   , (Index, )
                                   , { 'magic_author': author
                                     , 'name':         index_name
                                     , 'localname':    author.get_displayable_name()
                                     , 'shortname':    author.last_name
                                     , 'generate':     author_book_generator
                                   ,})
            self.indices.append(author_generator)
            self.add_author_record(( author.get_full_name()                 # name
                                   , author.get_displayable_name()          # display_name
                                   , '{}-{}'.format(self.name, index_name)  # docname
                                   , author_id))                            # author's unique id

    def add_series_record(self, record: Tuple[str, str, str, int]) -> None:
        self.data['series'].append(record)

    def get_series_record(self, series: str) -> Tuple[str, str, str, int]:
        return next((x for x in self.data['series'] if x[1] == series), None)

    def create_series_unique_id(self) -> int:
        return len(self.data['series'])

    def get_series_unique_id(self, series: str) -> int:
        record = self.get_series_record(series)
        if record is not None:
            return record[3]
        else:
            return self.create_series_unique_id()

    def add_series(self, series:str) -> None:
        record = self.get_series_record(series)

        if record is None:
            series_id = self.create_series_unique_id()
            index_name = '{}_{}'.format('series', series_id)
            series_generator = type('series_index_generator_%s' % series_id
                                    , (Index, )
                                    , {'magic_series':  series
                                        , 'name':       index_name
                                        , 'localname':  series
                                        , 'shortname':  series
                                        , 'generate':   series_book_generator
                                        ,})

            self.indices.append(series_generator)
            self.add_series_record(( series.replace(' ', '_')               # name
                                   , series                                 # display name
                                   , '{}-{}'.format(self.name, index_name)  # docname
                                   , series_id))                            # series unique id

    def add_tag_record(self, record: Tuple[str,str,str,int]) -> None:
        self.data['tags'].append(record)

    def get_tag_record(self, tag: str) -> Tuple[str,str,str,int]:
        return next((x for x in self.data['tags'] if x[1] == tag), None)

    def create_tag_unique_id(self) -> int:
        return len(self.data['tags'])

    def get_tag_unique_id(self, tag:str) -> int:
        record = self.get_tag_record(tag)
        if record is not None:
            return record[3]
        else:
            return self.create_tag_unique_id()

    def add_tag(self, tag:str) -> None:
        if tag == '':
            return

        record = self.get_tag_record(tag)

        if record is None:
            tag_id = self.create_tag_unique_id()
            index_name = '{}_{}'.format('tag', tag_id)

            tags_generator = type('tags_index_generator_%s' % tag_id
                                    , (Index, )
                                    , {'magic_tag': tag
                                        , 'name': index_name
                                        , 'localname': tag
                                        , 'shortname': tag
                                        , 'generate': tags_book_generator
                                        ,})

            self.indices.append(tags_generator)
            self.add_tag_record(( tag.replace(' ', '_')
                                , tag
                                , '{}-{}'.format(self.name, index_name)  # docname
                                , tag_id))

    def add_book(self, book: "Book") -> None:
        for a in book.authors:
            self.add_author(a)

        for i in book.issues:
            if not i.series == '':
                self.add_series(i.series)

        for t in book.tags:
            self.add_tag(t)
        
        authors_str = '.'.join([a.last_name for a in book.authors])
        name = '{}.{}.{}'.format('book', book.title, authors_str)

        exists = next((x for x in self.data['books'] if x[0] == name), False)

        if not exists:
            series = [i.series for i in book.issues if i.series != '']

            self.data['books'].append(( name
                                      , book.transform_title()
                                      , self.env.docname
                                      , book.id
                                      , book.authors
                                      , series
                                      , book.tags))


def setup(app: "Sphinx") -> Dict[str, Any]:
    app.add_domain(Athenaeum)

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

# TODO book display name for cases `The` and `A`
