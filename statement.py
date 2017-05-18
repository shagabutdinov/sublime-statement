import sublime
import sublime_plugin

import re
from Statement import parser

try:
  from Expression import expression
except ImportError as error:
  sublime.error_message("Dependency import failed; please read readme for " +
   "Statement plugin for installation instructions; to disable this " +
   "message remove this plugin; message: " + str(error))
  raise error

RANGE = 10240

def is_arguments(view, point, nesting = None):
  if nesting == None:
    nesting = expression.get_nesting(view, point, RANGE)

  if nesting == None:
    return False

  nesting_opener_region = sublime.Region(nesting[0] - 1, nesting[0])
  nesting_opener = view.substr(nesting_opener_region)
  if nesting_opener == '[':
    return True

  preceding_64_bytes_region = sublime.Region(nesting[0] - 65, nesting[0] - 1)
  preceding_64_bytes = view.substr(preceding_64_bytes_region)

  if nesting_opener == '(':
    return re.search(r'\w\s*$', preceding_64_bytes) != None
  elif nesting_opener == '{':
    return re.search(r'([\w)]|=>|->)\s*$', preceding_64_bytes) == None
  else:
    raise Exception('Unknown nesting opener "' + nesting_opener + '"')

  return False

def get_root_statement(view, point):
  current = get_statement(view, point)
  if current == None:
    return

  while True:
    nesting = expression.get_nesting(view, current[0], RANGE, {})
    if nesting == None:
      return current

    if not is_arguments(view, current[0], nesting):
      return current

    new = get_statement(view, nesting[0] - 1)
    if new == None:
      return current

    current = new

def get_parent_token(view, cursor, expr = r'[({\[]'):
  nesting = expression.get_nesting(view, cursor, RANGE, {}, expr)
  if not is_arguments(view, cursor, nesting):
    return None

  _, token = get_token(view, nesting[0] - 1)
  return token

def get_parent_argument(view, cursor, expr = r'[({\[]'):
  nesting = expression.get_nesting(view, cursor, RANGE, {}, expr)
  if not is_arguments(view, cursor, nesting):
    return None

  _, argument = get_argument(view, nesting[0] - 1)
  return argument

def get_parent_statement(view, cursor, expr = r'[({\[]'):
  nesting = expression.get_nesting(view, cursor, RANGE, {}, expr)
  if not is_arguments(view, cursor, nesting):
    return None

  return get_statement(view, nesting[0] - 1)

def get_tokens(view, cursor = None, statement = None):
  if cursor == None:
    cursor = statement[0]

  info = parser.parse(view, cursor)
  if info == None:
    return []

  tokens, _ = info
  result = []
  for token in tokens:
    found = (
      statement == None or
      statement[0] <= token[0] and
      token[1] <= statement[1]
    )

    if found:
      result.append(token)

  return result

def get_token(view, cursor, tokens = None):
  if tokens == None:
    tokens = get_tokens(view, cursor)

  if len(tokens) == 0:
    return None, None

  if cursor < tokens[0][0]:
    return 0, tokens[0]

  for index, token in enumerate(tokens):
    if cursor < token[0]:
      previous = tokens[index - 1]
      delimeter = view.substr(sublime.Region(previous[1], token[0]))
      if re.search(r'^\s*$', delimeter):
        return index, token

      clear_delimeter_position = re.search(r'\S\s*$', delimeter).start(0)
      if cursor <= clear_delimeter_position + previous[1]:
        return index, previous
      else:
        return index, token

    if token[0] <= cursor and cursor <= token[1]:
      return index, token

  last_index = len(tokens) - 1
  return last_index, tokens[last_index]

def get_arguments(view, cursor, statement = None):
  tokens = get_tokens(view, cursor, statement)
  if len(tokens) == 0:
    return []

  region = sublime.Region(tokens[0][0], tokens[-1][1])
  container = view.substr(region)
  arguments, start = [], tokens[0][0]

  for index, token in enumerate(tokens[: -1]):
    next_token = tokens[index + 1]
    delimeter = container[token[1] - region.a:next_token[0] - region.a].strip()
    if delimeter == ',':
      arguments.append([start, token[1]])
      start = next_token[0]

  arguments.append([start, tokens[-1][1]])

  return arguments

def get_argument(view, cursor, arguments = None):
  if arguments == None:
    arguments = get_arguments(view, cursor)

  return get_token(view, cursor, arguments)

def get_assignments(view, cursor):
  tokens = get_tokens(view, cursor)
  if len(tokens) == 0:
    return []

  region = sublime.Region(tokens[0][0], tokens[-1][1])
  statement = view.substr(region)
  assignments, start = [], tokens[0][0]

  for index, token in enumerate(tokens[: -1]):
    next_token = tokens[index + 1]
    delimeter = statement[token[1] - region.a:next_token[0] - region.a].strip()
    if delimeter == '=':
      assignments.append([start, token[1]])
      start = next_token[0]

  assignments.append([start, tokens[-1][1]])

  return assignments

def get_assignment(view, cursor, assignments = None):
  if assignments == None:
    assignments = get_assignments(view, cursor)

  return get_token(view, cursor, assignments)

def get_statement(view, cursor):
  _, statement = parser.parse(view, cursor)
  return statement

def get_token_delete_region(view, point, tokens = None):
  if tokens == None:
    tokens = get_tokens(view, point)

  if tokens == None:
    return

  index, _ = get_token(view, point, tokens)
  return _get_token_delete_region(view, tokens, index)

def _get_token_delete_region(view, tokens, index):
  last_index = len(tokens) - 1
  if index > last_index or index < 0:
    return

  token = tokens[index]
  use_next, previous, delimeter = False, None, None
  if index > 0:
    previous = tokens[index - 1]
    delimeter = [previous[1], token[0]]
    delimeter_value = view.substr(sublime.Region(*delimeter)).strip()
    delimeter_shift = re.search(r'^\s*', delimeter_value).end(0)

    if delimeter_value == '=' or delimeter_value == ',':
      use_next = True

    scope = view.scope_name(delimeter[0] + delimeter_shift)
    if 'keyword' in scope:
      if 'control' in scope:
        use_next = True

    if index == last_index:
      use_next = False

  if index == 0 or use_next:
    start, end = token[0], token[1]
    next = index + 1 <= last_index and tokens[index + 1]
    if next != False:
      end = next[0]
  else:
    start, end = previous[1], token[1]

  if end != view.size():
    line = view.line(end)
    if line.b == end:
      end += 1
      end += re.search('^\s*', view.substr(view.line(end))).end(0)
  else:
    line = view.line(start)
    if view.substr(sublime.Region(line.a, start)).strip() == '':
      start = line.a - 1

  return sublime.Region(start, end)