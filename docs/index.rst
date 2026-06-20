.. textparser documentation master file, created by
   sphinx-quickstart on Sat Apr 25 11:54:09 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2

Text parser
===========

.. include:: ../README.rst

The parser class
================

.. autoclass:: textparser.Parser
    :members:

Building the grammar
====================

The grammar built by combining the classes below and strings.

Here is a fictitious example grammar:

.. code-block:: python

   grammar = Sequence(
       'BEGIN',
       Optional(choice('IF', Sequence(ZeroOrMore('NUMBER')))),
       OneOrMore(Sequence('WORD', Not('NUMBER'))),
       Any(),
       DelimitedList('WORD', delim=':'),
       'END')

.. autoclass:: textparser.Sequence

.. autoclass:: textparser.Choice

.. autoclass:: textparser.ChoiceDict

.. autofunction:: textparser.choice

.. autoclass:: textparser.ZeroOrMore

.. autoclass:: textparser.ZeroOrMoreDict

.. autoclass:: textparser.OneOrMore

.. autoclass:: textparser.OneOrMoreDict

.. autoclass:: textparser.DelimitedList

.. autoclass:: textparser.Optional

.. autoclass:: textparser.Any

.. autoclass:: textparser.AnyUntil

.. autoclass:: textparser.And

.. autoclass:: textparser.Not

.. autoclass:: textparser.NoMatch

.. autoclass:: textparser.Tag

.. autoclass:: textparser.Forward

.. autoclass:: textparser.Repeated

.. autoclass:: textparser.RepeatedDict

.. autoclass:: textparser.Pattern
    :members:

.. autoclass:: textparser.MatchObject

.. autoclass:: textparser.Grammar

.. autoclass:: textparser.Token

.. autodata:: textparser.MISMATCH

Exceptions
==========

.. autoclass:: textparser.Error
    :members:

.. autoclass:: textparser.ParseError
    :members:

.. autoclass:: textparser.TokenizeError
    :members:

.. autoclass:: textparser.GrammarError
    :members:

Utility functions
=================

.. autofunction:: textparser.markup_line

.. autofunction:: textparser.tokenize_init
