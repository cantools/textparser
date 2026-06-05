import pickle
import unittest
from collections import namedtuple

import textparser
from textparser import Grammar
from textparser import Sequence
from textparser import Choice
from textparser import choice
from textparser import ChoiceDict
from textparser import ZeroOrMore
from textparser import ZeroOrMoreDict
from textparser import OneOrMore
from textparser import OneOrMoreDict
from textparser import DelimitedList
from textparser import Token
from textparser import TokenizeError
from textparser import tokenize_init
from textparser import Any
from textparser import AnyUntil
from textparser import Optional
from textparser import Tag
from textparser import Forward
from textparser import NoMatch
from textparser import Not
from textparser import And
from textparser import markup_line
from textparser import replace_blocks


def tokenize(items, add_eof_token=True):
    tokens = []

    for item in items:
        if len(item) == 2:
            token = Token(*item, offset=1)
        else:
            token = Token(*item)

        tokens.append(token)

    if add_eof_token:
        tokens.append(Token('__EOF__', None, -1))

    return tokens


class TextParserTest(unittest.TestCase):

    def parse_and_assert_tree(self, grammar, datas):
        for tokens, expected_tree in datas:
            tree = grammar.parse(tokenize(tokens))
            self.assertEqual(tree, expected_tree)

    def parse_and_assert_mismatch(self, grammar, datas):
        for tokens, line in datas:
            tokens = tokenize(tokens)

            with self.assertRaises(textparser.GrammarError) as cm:
                grammar.parse(tokens)

            self.assertEqual(cm.exception.offset, line)

    def test_grammar_sequence(self):
        grammar = Grammar(Sequence('NUMBER', 'WORD'))
        tokens = tokenize([
            ('NUMBER', '1.45'),
            ('WORD', 'm')
        ])
        tree = grammar.parse(tokens)
        self.assertEqual(tree, ['1.45', 'm'])

    def test_grammar_sequence_mismatch(self):
        grammar = Grammar(Sequence('NUMBER', 'WORD'))
        tokens = tokenize([('NUMBER', '1.45')])

        with self.assertRaises(textparser.GrammarError) as cm:
            grammar.parse(tokens)

        self.assertEqual(cm.exception.offset, -1)

    def test_grammar_choice(self):
        grammar = Grammar(Choice('NUMBER', 'WORD'))

        datas = [
            (
                [('WORD', 'm')],
                'm'
            ),
            (
                [('NUMBER', '5')],
                '5'
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_choice_mismatch(self):
        grammar = Grammar(Choice(Sequence('NUMBER', 'WORD'),
                                 'WORD'))

        datas = [
            ([('NUMBER', '1', 5)], -1),
            ([('NUMBER', '1', 5), ('NUMBER', '2', 7)], 7)
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_choice_dict(self):
        number = Forward()
        number <<= Sequence('NUMBER')
        grammar = Grammar(ChoiceDict(number,
                                     Tag('foo', Sequence('WORD')),
                                     ChoiceDict('BAR'),
                                     'FIE'))

        datas = [
            (
                [('WORD', 'm')],
                ('foo', ['m'])
            ),
            (
                [('NUMBER', '5')],
                ['5']
            ),
            (
                [('BAR', 'foo')],
                'foo'
            ),
            (
                [('FIE', 'fum')],
                'fum'
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_choice_dict_mismatch(self):
        grammar = Grammar(ChoiceDict(Sequence('NUMBER'),
                                     Sequence('WORD')))
        tokens = tokenize([(',', ',', 3)])

        with self.assertRaises(textparser.Error) as cm:
            grammar.parse(tokens)

        self.assertEqual(cm.exception.offset, 3)

    def test_grammar_choice_dict_init(self):
        datas = [
            (
                ('WORD', 'WORD'),
                "First token kind must be unique, but WORD isn't."
            ),
            (
                ('WORD', Sequence('WORD')),
                "First token kind must be unique, but WORD isn't."
            ),
            (
                (Sequence(Sequence(Optional('WORD'))), ),
                "Unsupported pattern type <class 'textparser.Optional'>."
            )
        ]

        for grammar, message in datas:
            with self.assertRaises(textparser.Error) as cm:
                ChoiceDict(*grammar)

            self.assertEqual(str(cm.exception), message)

    def test_grammar_delimited_list(self):
        grammar = Grammar(Sequence(DelimitedList('WORD'), Optional('.')))

        datas = [
            (
                [('WORD', 'foo')],
                [['foo'], []]
            ),
            (
                [('WORD', 'foo'), (',', ','), ('WORD', 'bar')],
                [['foo', 'bar'], []]
            ),
            (
                [('WORD', 'foo'), (',', ','), ('WORD', 'bar'), ('.', '.')],
                [['foo', 'bar'], ['.']]
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_delimited_list_mismatch(self):
        grammar = Grammar(Sequence(DelimitedList('WORD'), Optional('.')))

        datas = [
            (
                [
                    ('WORD', 'foo', 1),
                    (',', ',', 2)
                ],
                2
            ),
            (
                [
                    ('WORD', 'foo', 1),
                    (',', ',', 2),
                    ('WORD', 'foo', 3),
                    (',', ',', 4),
                    ('.', '.', 5)
                ],
                4
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_zero_or_more(self):
        grammar = Grammar(ZeroOrMore('WORD'))

        datas = [
            (
                [],
                []
            ),
            (
                [('WORD', 'foo')],
                ['foo']
            ),
            (
                [('WORD', 'foo'), ('WORD', 'bar')],
                ['foo', 'bar']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_zero_or_more_partial_element_match(self):
        grammar = Grammar(Sequence(
            ZeroOrMore(Sequence('WORD', 'NUMBER')), 'WORD'))

        datas = [
            (
                [
                    ('WORD', 'foo'),
                    ('NUMBER', '1'),
                    ('WORD', 'bar'),
                    ('NUMBER', '2'),
                    ('WORD', 'fie')],
                [[['foo', '1'], ['bar', '2']], 'fie']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_zero_or_more_dict(self):
        grammar = Grammar(ZeroOrMoreDict(Sequence('WORD', 'NUMBER')))

        datas = [
            (
                [],
                {}
            ),
            (
                [('WORD', 'foo'), ('NUMBER', '1'),
                 ('WORD', 'bar'), ('NUMBER', '2'),
                 ('WORD', 'foo'), ('NUMBER', '3')],
                {
                    'foo': [['foo', '1'], ['foo', '3']],
                    'bar': [['bar', '2']]
                }
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_one_or_more(self):
        grammar = Grammar(OneOrMore('WORD'))

        datas = [
            (
                [('WORD', 'foo')],
                ['foo']
            ),
            (
                [('WORD', 'foo'), ('WORD', 'bar')],
                ['foo', 'bar']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_one_or_more_mismatch(self):
        grammar = Grammar(OneOrMore('WORD'))

        datas = [
            (
                []
                , -1
            ),
            (
                [('NUMBER', 'foo', 2)],
                2
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_one_or_more_dict(self):
        grammar = Grammar(OneOrMoreDict(Sequence('WORD', 'NUMBER')))

        datas = [
            (
                [('WORD', 'foo'), ('NUMBER', '1')],
                {
                    'foo': [['foo', '1']]
                }
            ),
            (
                [('WORD', 'foo'), ('NUMBER', '1'),
                 ('WORD', 'bar'), ('NUMBER', '2'),
                 ('WORD', 'foo'), ('NUMBER', '3')],
                {
                    'foo': [['foo', '1'], ['foo', '3']],
                    'bar': [['bar', '2']]
                }
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_one_or_more_dict_mismatch(self):
        grammar = Grammar(OneOrMoreDict(Sequence('WORD', 'NUMBER')))

        datas = [
            (
                [('WORD', 'foo', 5)],
                -1
            ),
            (
                [
                    ('WORD', 'foo', 5),
                    ('WORD', 'bar', 6)
                ],
                6
            ),
            (
                [
                    ('WORD', 'foo', 5),
                    ('NUMBER', '4', 6),
                    ('WORD', 'bar', 7),
                    ('WORD', 'fie', 8)
                ],
                8
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_any(self):
        grammar = Grammar(Any())

        datas = [
            (
                [('A', r'a')],
                'a'
            ),
            (
                [('B', r'b')],
                'b'
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_any_until(self):
        grammar = Grammar(Sequence(AnyUntil('STRING'), 'STRING'))

        datas = [
            (
                [('NUMBER', '1'),
                 ('WORD', 'a'),
                 ('STRING', '"b"')],
                [['1', 'a'], '"b"']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_any_until_sequence(self):
        grammar = Grammar(Sequence(AnyUntil(Sequence('WORD', 'STRING')),
                                   'WORD',
                                   'STRING'))

        datas = [
            (
                [('NUMBER', '1'),
                 ('WORD', 'a'),
                 ('WORD', 'b'),
                 ('STRING', '"b"')],
                [['1', 'a'], 'b', '"b"']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_1(self):
        grammar = Grammar(Sequence(
            'IF',
            choice(Sequence(choice('A', 'B'), 'STRING'),
                   'STRING'),
            'WORD',
            choice(
                Sequence(
                    choice(DelimitedList('STRING'), ZeroOrMore('NUMBER')), '.'),
            '.')))

        datas = [
            (
                [
                    ('IF', 'IF'),
                    ('STRING', 'foo'),
                    ('WORD', 'bar'),
                    ('.', '.')
                ],
                ['IF', 'foo', 'bar', [[], '.']]
            ),
            (
                [
                    ('IF', 'IF'),
                    ('STRING', 'foo'),
                    ('WORD', 'bar'),
                    ('NUMBER', '0'),
                    ('NUMBER', '100'),
                    ('.', '.')
                ],
                ['IF', 'foo', 'bar', [['0', '100'], '.']]
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_1_mismatch(self):
        grammar = Grammar(Sequence(
            'IF',
            choice(Sequence(choice('A', 'B'), 'STRING'),
                   'STRING'),
            'WORD',
            choice(
                Sequence(
                    choice(DelimitedList('STRING'), ZeroOrMore('NUMBER')), '.'),
            '.')))

        datas = [
            (
                [
                    ('IF', 'IF', 1),
                    ('STRING', 'foo', 2),
                    ('WORD', 'bar', 3),
                    (',', ',', 4)
                ],
                4
            ),
            (
                [
                    ('IF', 'IF', 1),
                    ('STRING', 'foo', 2),
                    ('.', '.', 3)
                ],
                3
            ),
            (
                [
                    ('IF', 'IF', 1),
                    ('NUMBER', '1', 2)
                ],
                2
            ),
            (
                [
                    ('IF', 'IF', 1),
                    ('STRING', 'foo', 2),
                    ('WORD', 'bar', 3),
                    ('.', '.', 4),
                    ('.', '.', 5)
                ],
                5
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_forward(self):
        foo = Forward()
        foo <<= Sequence('FOO')
        grammar = Grammar(foo)

        datas = [
            (
                [('FOO', 'foo')],
                ['foo']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_forward_text(self):
        foo = Forward()
        foo <<= 'FOO'
        grammar = Grammar(foo)

        datas = [
            (
                [('FOO', 'foo')],
                'foo'
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_optional(self):
        grammar = Grammar(Sequence(Optional('WORD'),
                                   Optional('WORD'),
                                   Optional('NUMBER')))

        datas = [
            (
                [],
                [[], [], []]
            ),
            (
                [('WORD', 'a')],
                [['a'], [], []]
            ),
            (
                [('NUMBER', 'c')],
                [[], [], ['c']]
            ),
            (
                [('WORD', 'a'), ('NUMBER', 'c')],
                [['a'], [], ['c']]
            ),
            (
                [('WORD', 'a'), ('WORD', 'b'), ('NUMBER', 'c')],
                [['a'], ['b'], ['c']]
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_tag(self):
        grammar = Grammar(Tag('a',
                              Tag('b',
                                  choice(Tag('c', 'WORD'),
                                         Tag('d', Optional('NUMBER'))))))

        datas = [
            (
                [('WORD', 'bar')],
                ('a', ('b', ('c', 'bar')))
            ),
            (
                [('NUMBER', '1')],
                ('a', ('b', ('d', ['1'])))
            ),
            (
                [],
                ('a', ('b', ('d', [])))
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_tag_mismatch(self):
        grammar = Grammar(Tag('a', 'WORD'))

        datas = [
            (
                [('NUMBER', 'bar')],
                1
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_and(self):
        grammar = Grammar(Sequence(And('NUMBER'), 'NUMBER'))

        datas = [
            (
                [('NUMBER', '1')],
                [[], '1']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_and_mismatch(self):
        grammar = Grammar(Sequence(And('NUMBER'), 'NUMBER'))

        datas = [
            (
                [('WORD', 'foo', 3), ('NUMBER', '1', 4)],
                3
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_not(self):
        grammar = Grammar(Sequence(Not('WORD'), 'NUMBER'))

        datas = [
            (
                [('NUMBER', '1')],
                [[], '1']
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_not_mismatch(self):
        grammar = Grammar(Sequence(Not('WORD'), 'NUMBER'))

        datas = [
            (
                [('WORD', 'foo', 3), ('NUMBER', '1', 4)],
                3
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_grammar_no_match(self):
        grammar = Grammar(NoMatch())

        datas = [
            (
                [('NUMBER', '1', 3)],
                3
            ),
            (
                [('WORD', 'foo', 3)],
                3
            )
        ]

        self.parse_and_assert_mismatch(grammar, datas)

    def test_parse_start_and_end_of_file(self):
        class Parser(textparser.Parser):

            def grammar(self):
                return Sequence('__SOF__', '__EOF__')

        self.assertEqual(Parser().parse('', match_sof=True),
                         ['__SOF__', '__EOF__'])

    def test_parse_start_of_file_mismatch(self):
        class Parser(textparser.Parser):

            def grammar(self):
                return Sequence('__EOF__')

        with self.assertRaises(textparser.ParseError) as cm:
            Parser().parse('123', match_sof=True)

        self.assertEqual(str(cm.exception),
                         'Invalid syntax at line 1, column 1: ">>!<<123"')

    def test_parse_end_of_file(self):
        class Parser(textparser.Parser):

            def grammar(self):
                return '__EOF__'

        self.assertEqual(Parser().parse('', match_sof=False), '__EOF__')

    def test_grammar_none(self):
        class AnyAsNone(textparser.Pattern):

            def match(self, tokens):
                tokens.get_value()

                return None

        grammar = Grammar(AnyAsNone())

        datas = [
            (
                [('NUMBER', '1')],
                None
            )
        ]

        self.parse_and_assert_tree(grammar, datas)

    def test_grammar_error(self):
        grammar = Grammar(NoMatch())

        datas = [
            [('NUMBER', '1', 3)],
            [('WORD', 'foo', 3)]
        ]

        for tokens in datas:
            tokens = tokenize(tokens)

            with self.assertRaises(textparser.GrammarError) as cm:
                grammar.parse(tokens)

            self.assertEqual(cm.exception.offset, 3)
            self.assertEqual(str(cm.exception),
                             'Invalid syntax at offset 3.')

    def test_tokenize_error(self):
        datas = [
            (2, 'hej', 'Invalid syntax at line 1, column 3: "he>>!<<j"'),
            (0, 'a\nb\n', 'Invalid syntax at line 1, column 1: ">>!<<a"'),
            (1, 'a\nb\n', 'Invalid syntax at line 1, column 2: "a>>!<<"'),
            (2, 'a\nb\n', 'Invalid syntax at line 2, column 1: ">>!<<b"')
        ]

        for offset, text, message in datas:
            with self.assertRaises(TokenizeError) as cm:
                raise TokenizeError(text, offset)

            self.assertEqual(cm.exception.text, text)
            self.assertEqual(cm.exception.offset, offset)
            self.assertEqual(str(cm.exception), message)

    def test_create_token_re(self):
        datas = [
            (
                [('A', r'a')],
                '(?P<A>a)'
            ),
            (
                [('A', r'b'), ('C', r'd')],
                '(?P<A>b)|(?P<C>d)'
            )
        ]

        for spec, expected_re_token in datas:
            tokens, re_token = tokenize_init(spec)
            self.assertEqual(tokens,
                             [Token(kind='__SOF__', value='__SOF__', offset=0)])
            self.assertEqual(re_token, expected_re_token)

    def test_parser(self):
        class Parser(textparser.Parser):

            def keywords(self):
                return set([
                    'IF',
                    'A',
                    'B'
                ])

            def token_specs(self):
                return [
                    ('SKIP',                r'[ \r\n\t]+'),
                    ('NUMBER',              r'-?\d+(\.\d+)?([eE][+-]?\d+)?'),
                    ('DOT',            '.', r'\.'),
                    ('WORD',                r'[A-Za-z0-9_]+'),
                    ('ESCAPED_STRING',      r'"(\\"|[^"])*?"'),
                    ('MISMATCH',            r'.')
                ]

            def grammar(self):
                return Sequence(
                    'IF',
                    Optional(choice('A', 'B')),
                    'ESCAPED_STRING',
                    'WORD',
                    Optional(choice(DelimitedList('ESCAPED_STRING'),
                                    ZeroOrMore('NUMBER'))),
                    '.')

        datas = [
            (
                'IF "foo" bar .',
                ['IF', [], '"foo"', 'bar', [[]], '.'],
                [
                    Token(kind='IF', value='IF', offset=0),
                    [],
                    Token(kind='ESCAPED_STRING', value='"foo"', offset=3),
                    Token(kind='WORD', value='bar', offset=9),
                    [[]],
                    Token(kind='.', value='.', offset=13)
                ]
            ),
            (
                'IF B "" b 1 2 .',
                ['IF', ['B'], '""', 'b', [['1', '2']], '.'],
                [
                    Token(kind='IF', value='IF', offset=0),
                    [
                        Token(kind='B', value='B', offset=3)
                    ],
                    Token(kind='ESCAPED_STRING', value='""', offset=5),
                    Token(kind='WORD', value='b', offset=8),
                    [
                        [
                            Token(kind='NUMBER', value='1', offset=10),
                            Token(kind='NUMBER', value='2', offset=12)
                        ]
                    ],
                    Token(kind='.', value='.', offset=14)
                ]
            )
        ]

        for text, expected_tree, expected_token_tree in datas:
            tree = Parser().parse(text)
            self.assertEqual(tree, expected_tree)
            tree = Parser().parse(text, token_tree=True)
            self.assertEqual(tree, expected_token_tree)

    def test_parser_default_keywords(self):
        class Parser(textparser.Parser):

            def token_specs(self):
                return [
                    ('SKIP',                r'[ \r\n\t]+'),
                    ('NUMBER',              r'-?\d+(\.\d+)?([eE][+-]?\d+)?'),
                    ('DOT',            '.', r'\.'),
                    ('WORD',                r'[A-Za-z0-9_]+'),
                    ('ESCAPED_STRING',      r'"(\\"|[^"])*?"'),
                    ('MISMATCH',            r'.')
                ]

            def grammar(self):
                return Sequence(
                    'WORD',
                    Optional('WORD'),
                    'ESCAPED_STRING',
                    'WORD',
                    Optional(choice(DelimitedList('ESCAPED_STRING'),
                                    ZeroOrMore('NUMBER'))),
                    '.')

        datas = [
            (
                'IF "foo" bar .',
                ['IF', [], '"foo"', 'bar', [[]], '.'],
                [
                    Token(kind='WORD', value='IF', offset=0),
                    [],
                    Token(kind='ESCAPED_STRING', value='"foo"', offset=3),
                    Token(kind='WORD', value='bar', offset=9),
                    [[]],
                    Token(kind='.', value='.', offset=13)
                ]
            ),
            (
                'IF B "" b 1 2 .',
                ['IF', ['B'], '""', 'b', [['1', '2']], '.'],
                [
                    Token(kind='WORD', value='IF', offset=0),
                    [
                        Token(kind='WORD', value='B', offset=3)
                    ],
                    Token(kind='ESCAPED_STRING', value='""', offset=5),
                    Token(kind='WORD', value='b', offset=8),
                    [
                        [
                            Token(kind='NUMBER', value='1', offset=10),
                            Token(kind='NUMBER', value='2', offset=12)
                        ]
                    ],
                    Token(kind='.', value='.', offset=14)
                ]
            )
        ]

        for text, expected_tree, expected_token_tree in datas:
            tree = Parser().parse(text)
            self.assertEqual(tree, expected_tree)
            tree = Parser().parse(text, token_tree=True)
            self.assertEqual(tree, expected_token_tree)

    def test_parser_bare(self):
        class Parser(textparser.Parser):

            pass

        with self.assertRaises(NotImplementedError) as cm:
            Parser().parse('foo')

        self.assertEqual(str(cm.exception), 'No grammar defined.')

    def test_parser_default_token_specs(self):
        class Parser(textparser.Parser):

            def grammar(self):
                return 'WORD'

        tree = Parser().parse('foo')
        self.assertEqual(tree, 'foo')

    def test_parser_tokenize_mismatch(self):
        class Parser(textparser.Parser):

            def token_specs(self):
                return [
                    ('SKIP',                r'[ \r\n\t]+'),
                    ('NUMBER',              r'-?\d+(\.\d+)?([eE][+-]?\d+)?'),
                    ('MISMATCH',            r'.')
                ]

            def grammar(self):
                return Grammar('NUMBER')

        with self.assertRaises(textparser.ParseError) as cm:
            Parser().parse('12\n34foo\n789')

        self.assertEqual(cm.exception.offset, 5)
        self.assertEqual(cm.exception.line, 2)
        self.assertEqual(cm.exception.column, 3)
        self.assertEqual(str(cm.exception),
                         'Invalid syntax at line 2, column 3: "34>>!<<foo"')

    def test_parser_grammar_mismatch(self):
        class Parser(textparser.Parser):

            def tokenize(self, _text):
                return tokenize([
                    ('NUMBER', '1.45', 0),
                    ('NUMBER', '2', 5)
                ])

            def grammar(self):
                return Sequence('NUMBER', 'WORD')

        with self.assertRaises(textparser.ParseError) as cm:
            Parser().parse('1.45 2')

        self.assertEqual(cm.exception.offset, 5)
        self.assertEqual(cm.exception.line, 1)
        self.assertEqual(cm.exception.column, 6)
        self.assertEqual(str(cm.exception),
                         'Invalid syntax at line 1, column 6: "1.45 >>!<<2"')

    def test_parser_grammar_mismatch_choice_max(self):
        class Parser(textparser.Parser):

            def __init__(self, tokens):
                self._tokens = tokens

            def tokenize(self, _text):
                return tokenize(self._tokens, add_eof_token=False)

            def grammar(self):
                return Choice(Sequence('NUMBER', 'WORD'),
                              'WORD')

        Data = namedtuple('Data',
                          [
                              'text',
                              'tokens',
                              'offset',
                              'line',
                              'column',
                              'message',
                          ])

        datas = [
            Data(
                text='1.45',
                tokens=[
                    ('NUMBER', '1.45', 0)
                ],
                offset=4,
                line=1,
                column=5,
                message='Invalid syntax at line 1, column 5: "1.45>>!<<"'
            ),
            Data(
                text='1.45 2',
                tokens=[
                    ('NUMBER', '1.45', 0),
                    ('NUMBER', '2', 5)
                ],
                offset=5,
                line=1,
                column=6,
                message='Invalid syntax at line 1, column 6: "1.45 >>!<<2"'
            )
        ]

        for text, tokens, offset, line, column, message in datas:
            with self.assertRaises(textparser.ParseError) as cm:
                Parser(tokens).parse(text)

            self.assertEqual(cm.exception.offset, offset)
            self.assertEqual(cm.exception.line, line)
            self.assertEqual(cm.exception.column, column)
            self.assertEqual(str(cm.exception), message)

    def test_parse_error(self):
        class Parser(textparser.Parser):

            def tokenize(self, text):
                raise TokenizeError(text, 5)

            def grammar(self):
                return Grammar(Sequence('NUMBER', 'WORD'))

        with self.assertRaises(textparser.ParseError) as cm:
            Parser().parse('12\n3456\n789')

        self.assertEqual(cm.exception.text, '12\n3456\n789')
        self.assertEqual(cm.exception.offset, 5)
        self.assertEqual(cm.exception.line, 2)
        self.assertEqual(cm.exception.column, 3)
        self.assertEqual(str(cm.exception),
                         'Invalid syntax at line 2, column 3: "34>>!<<56"')

    def test_markup_line(self):
        datas = [
            (0, '>>!<<0', None),
            (1, '0>>!<<', None),
            (2, '>>!<<1234', None),
            (4, '12>>!<<34', None),
            (6, '1234>>!<<', None),
            (7, '>>!<<56', None),
            (8, '5>>!<<6', None),
            (9, '56>>!<<', None),
            (3, '1x234', 'x')
        ]

        for offset, line, marker in datas:
            if marker is None:
                text = markup_line('0\n1234\n56', offset)
            else:
                text = markup_line('0\n1234\n56',
                                   offset,
                                   marker=marker)

            self.assertEqual(text, line)

    def test_replace_blocks(self):
        datas = [
            ('{}', '{}'),
            ('{{}}', '{  }'),
            ('{{\n} xxx {}}', '{ \n        }'),
            ('1{a\n}2{b}3', '1{ \n}2{ }3')
        ]

        for old, expected in datas:
            new = replace_blocks(old)
            self.assertEqual(new, expected)

    def test_replace_blocks_start_end(self):
        datas = [
            ('1[a]2[b]3', '1[ ]2[ ]3', '[', ']'),
            ('1{a}2{b}3', '1{ }2{ }3', '{', '}'),
            ('1(a)2(b)3', '1( )2( )3', '(', ')'),
            ('1((a))2((b))3', '1(( ))2(( ))3', '((', '))')
        ]

        for old, expected, start, end in datas:
            new = replace_blocks(old, start, end)
            self.assertEqual(new, expected)

    def test_any_zero_or_more(self):
        class Parser(textparser.Parser):

            def keywords(self):
                return ['interesting_group']

            def token_specs(self):
                return [
                    ('SKIP',        r'[ \r\n\t]+'),
                    ('WORD',        r'[A-Za-z0-9_]+'),
                    ('SEMICOLON',   ';', r';'),
                    ('BRACE_OPEN',  '{', r'\{'),
                    ('BRACE_CLOSE', '}', r'\}'),
                    ('EQUAL',       '=', r'='),
                ]

            def grammar(self):
                interesting_group = textparser.Sequence(
                    'interesting_group', '{',
                    ZeroOrMore(Sequence('WORD', '=', 'WORD', ';')),
                    '}',
                    ';')

                return Sequence(AnyUntil('interesting_group'),
                                interesting_group,
                                ZeroOrMore(Any()))


        text = '''
        some_group {
             foo bar; foo bar;
        };

        interesting_group {
             a = 1;
             b = 2;
        };

        another_group {
             foo bar
        };
        '''

        tree = Parser().parse(text)
        self.assertEqual(tree[1],
                         [
                             'interesting_group',
                             '{',
                             [
                                 ['a', '=', '1', ';'],
                                 ['b', '=', '2', ';']
                             ],
                             '}',
                             ';'])

    def test_error_picklable(self):
        class Parser(textparser.Parser):

            def grammar(self):
                return Sequence('__EOF__')

        try:
            Parser().parse('123', match_sof=True)
        except Exception as exc:
            self.assertIsInstance(exc, textparser.ParseError)
            pickled = pickle.dumps(exc)
            unpickled = pickle.loads(pickled)
            self.assertIsInstance(unpickled, textparser.ParseError)
            self.assertEqual(repr(unpickled), repr(exc))


if __name__ == '__main__':
    unittest.main()
