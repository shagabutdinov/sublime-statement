# Sublime Statement plugin (beta)

Glorious plugin that tokenize your source code in language-independent way.
Works only for c-like languages. It is in beta so it can fail on detecting
statements or tokens in some rare cases. It also provides API for other plugins
to manipulate tokens and statements.


### Demo

![Demo](https://raw.github.com/shagabutdinov/sublime-statement/master/demo/demo.gif "Demo")


### Installation

This plugin is part of [sublime-enhanced](http://github.com/shagabutdinov/sublime-enhanced)
plugin set. You can install sublime-enhanced and this plugin will be installed
automatically.

If you would like to install this package separately check "Installing packages
separately" section of [sublime-enhanced](http://github.com/shagabutdinov/sublime-enhanced)
package.


### WARNING

This plugin is in beta. It can work inproperly. This plugin will work only in
source code and only with c-like languages.


### Features

In this plugin the enitity called "token" is variable, method call or value but
not operator, delimeter or punctuation; e.g. for "call1() + call2(call3()) +
variable + 100 + true" tokens is "call1()", "call2(call3())", "variable", "100"
and "true" if cursor is out of any brackets. Argument is something between
commas and brackets, e.g. for "call1(call2(), var1 + var2, true and false)"
arguments is "call2()", "var1 + var2", "true and false" if cursor in brackets of
call1 (but not in brackets of call2). Statement is several tokens groupped
together by magic of "Statement/parser.py" :(. There are really magic, sorry for
that, guys. I'm not enough smart to do a better code.

- Goto/select token/argument by index

- Select current token/argument/statement - this is handy when you want to
replace or copy an call argument. Hit hotkey several times to select more parent
token.

- Delete current token/argument/statement - this is handy when you want to get
rid of method argument

- Goto next token/argument - for "add after/before" token usecase

- Swap position of cursor to start or end of current token/argument

- Swap tokens/arguments - moves token/argument to next/previous position

- Duplicate statement - creates double of current statement

- Create line after/before statement - handy


### Usage


##### Tokens:

  ```
  # before
  |if call1() + call2(subcall()) + call3() # <- cursor at beginning of line

  # after goto third token
  if call1() + call2(subcall()) + |call3() # <- cursor at third token

  # after goto previous token
  if call1() + |call2(subcall()) + call3() # <- cursor at previous token

  # after swap position of cursor
  if call1() + call2(subcall())| + call3() # <- cursor at then end of token

  # after swap token forward
  if call1() + call3() + call2(subcall())| # <- cursor at then end of token

  # after delete token
  if call1() + call3()| # <- cursor at then end of previous token
  ```


##### Arguments:

  ```
  # before
  root(|100, call(sub()) + var, true) # <- cursor at beginning of c

  # after goto third argument
  root(100, call(sub()) + var, |true) # <- cursor at third argument

  # after goto previous argument
  root(100, |call(sub()) + var, true) # <- cursor at previous argument

  # after swap position of cursor
  root(100, call(sub()) + var|, true) # <- cursor at then end of argument

  # after swap argument forward
  root(100, true, call(sub()) + var|) # <- cursor at then end of argument

  # after delete argument
  root(100, true|) # <- cursor at then end of previous argument
  ```


### Commands

| Description                | Keyboard shortcut | Command palette                       |
|----------------------------|-------------------|---------------------------------------|
| Statement: Goto 1st token             | alt+ctrl+1        | Statement: Goto 1st token             |
| Statement: Goto 2nd token             | alt+ctrl+2        | Statement: Goto 2nd token             |
| Statement: Goto 3rd token             | alt+ctrl+3        | Statement: Goto 3rd token             |
| Statement: Goto 4th token             | alt+ctrl+4        | Statement: Goto 4th token             |
| Statement: Goto 5th token             | alt+ctrl+5        | Statement: Goto 5th token             |
| Statement: Goto 1st argument          | alt+ctrl+1        | Statement: Goto 1st argument          |
| Statement: Goto 2nd argument          | alt+ctrl+2        | Statement: Goto 2nd argument          |
| Statement: Goto 3rd argument          | alt+ctrl+3        | Statement: Goto 3rd argument          |
| Statement: Goto 4th argument          | alt+ctrl+4        | Statement: Goto 4th argument          |
| Statement: Goto 5th argument          | alt+ctrl+5        | Statement: Goto 5th argument          |
| Statement: Select 1st token           | alt+shift+1       | Statement: Select 1st token           |
| Statement: Select 2nd token           | alt+shift+2       | Statement: Select 2nd token           |
| Statement: Select 3rd token           | alt+shift+3       | Statement: Select 3rd token           |
| Statement: Select 4th token           | alt+shift+4       | Statement: Select 4th token           |
| Statement: Select 5th token           | alt+shift+5       | Statement: Select 5th token           |
| Statement: Select 1st argument        | alt+shift+1       | Statement: Select 1st argument        |
| Statement: Select 2nd argument        | alt+shift+2       | Statement: Select 2nd argument        |
| Statement: Select 3rd argument        | alt+shift+3       | Statement: Select 3rd argument        |
| Statement: Select 4th argument        | alt+shift+4       | Statement: Select 4th argument        |
| Statement: Select 5th argument        | alt+shift+5       | Statement: Select 5th argument        |
| Statement: Select token               | alt+s             | Statement: Select token               |
| Statement: Select argument            | alt+shift+s       | Statement: Select argument            |
| Statement: Select statement           | alt+ctrl+s        | Statement: Select statement           |
| Statement: Delete token               | alt+d             | Statement: Delete token               |
| Statement: Delete argument            | alt+shift+d       | Statement: Delete argument            |
| Statement: Delete statement           | alt+ctrl+d        | Statement: Delete statement           |
| Statement: Goto next token            | alt+.             | Statement: Goto next token            |
| Statement: Goto previous token        | alt+,             | Statement: Goto previous token        |
| Statement: Goto next argument         | alt+shift+.       | Statement: Goto next argument         |
| Statement: Goto previous argument     | alt+shift+,       | Statement: Goto previous argument     |
| Statement: Swap start/end of token    | alt+m             | Statement: Swap start/end of token    |
| Statement: Swap start/end of argument | alt+shift+m       | Statement: Swap start/end of argument |
| Statement: Swap token forward         | ctrl+alt+.        | Statement: Swap token forward         |
| Statement: Swap token backward        | ctrl+alt+,        | Statement: Swap token backward        |
| Statement: Swap argument forward      | ctrl+alt+shift+.  | Statement: Swap argument forward      |
| Statement: Swap argument backward     | ctrl+alt+shift+,  | Statement: Swap argument backward     |
| Statement: Duplicate statement        | ctrl+shift+d      | Statement: Duplicate statement        |
| Statement: Add line after statement   | ctrl+'            | Statement: Add line after statement   |
| Statement: Add line before statement  | ctrl+;            | Statement: Add line before statement  |



### API

Methods under statement file ("from Statement import statement"):


##### is_arguments(view, point, nesting = None):

Check whether it is arguments passed (something delimeted by ",") at given
point; returns boolean.


##### get_root_statement(view, point):

Returns the statement ([start, end]) on top statement nesting that contains
given point.


##### get_parent_token(view, cursor, expr = r'[({\[]'):

Returns parent token ([start, end]) that contains given point.


##### get_parent_argument(view, cursor, expr = r'[({\[]'):

Returns parent argument ([start, end]) that contains given point.


##### get_parent_statement(view, cursor, expr = r'[({\[]'):

Returns parent statement ([start, end]) that contains given point.


##### get_tokens(view, cursor = None, statement = None):

Returns tokens at given point; returns [token1, token2, ...] list; where token
is [start, end].


##### get_token(view, cursor, tokens = None):

Returns token index and token at given point; If no token found returns None;
returns: index, [start, end].


##### get_arguments(view, cursor, statement = None):

Returns arguments at given point; returns [arg1, arg2, ...] list where arg is
[start, end] list.


##### get_argument(view, cursor, arguments = None):

Returns argument index and argument at given point; if no argument found returns
None; returns index, [start, end].


##### get_assignments(view, cursor):

Get assignment info at given point. Returns two tokens that represents left and
right part of assignment; returns [left, right] list where left and right is
[start, end] list.


##### get_assignment(view, cursor, assignments = None):

Get left or right part of assignment at given point; returns [start, end] list.


##### get_statement(view, cursor):

Get statement at given point; returns [start, end] list.


##### get_token_delete_region(view, point, tokens = None):

Get region at given point that should be erased if you want to delete a token;
returns sublime.Region.


### Dependencies

- https://github.com/shagabutdinov/sublime-expression