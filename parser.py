import sublime
import sublime_plugin
import re

PATTERN = re.compile(
  r'\s*(' +
    r'(\(|\[|\{|\)|\]|\})|'
    r'(\\?[\w$@]+[?!]?|\$)|' +

    # double colon is for not ignoring colon at the end of string (php/python
    # conflict)
    r'(::|[^\w(){}\[\]])' +
  r')\s*'
)

STATEMENT_OPEN = ['(', '{', '[']
STATEMENT_CLOSE = [')', '}', ']']
STATEMENT_DELIMETERS = [';', ':', '"', '\'', '(', ')', '[', ']', '{', '}']

STATEMENT_KEYS = {
  False : {# forward
    'open': STATEMENT_OPEN,
    'close': STATEMENT_CLOSE,
  },

  True : {# backward
    'open': STATEMENT_CLOSE,
    'close': STATEMENT_OPEN,
  }
}

BRACKETS = {
  '(': ')',
  '{': '}',
  '[': ']',
  ')': '(',
  '}': '{',
  ']': '[',
}

class State():
  def __init__(self, view, region, text, backward, matches, statement):
    self.view = view
    self.strings = view.find_by_selector('string')
    self.backward = backward
    self.tokens = []
    self.statement = statement

    self.set_region(region, text, matches)

  def set_region(self, region, text, matches):
    self.region = region
    self.text = text
    self.matches = matches

    self.index = 0
    if matches != None:
      self.last_index = len(matches) - 1
    else:
      self.last_index = None

  def finish(self):
    self.set_region(None, None, None)

  def is_finished(self):
    return self.region == None

def parse(view, point):
  point = _shift_point(view, point)
  if point == None:
    return None

  preceding, preceding_statement = _parse(view, point, True)
  if len(preceding) == 0:
    point = _shift_point_forward(view, point)
    following, following_statement = _parse(view, point, False)
    if len(following) > 0:
      preceding, preceding_statement = _parse(view, following[0][0], True)
    else:
      point = _shift_point_backward(view, point)
      preceding, preceding_statement = _parse(view, point, True)
      if len(preceding) > 0:
        following, following_statement = _parse(view, preceding[-1][1], False)
  else:
    following, following_statement = _parse(view, preceding[-1][1], False)

  tokens = _join(view, preceding + following)
  statement = [preceding_statement[0], following_statement[1]]

  return tokens, statement

def _shift_point(view, point):
  line = view.line(point)
  if view.substr(line).strip() == '':
    next_line, _ = _get_next_line(view, False, line)
    if next_line == None:
      return None

    point = next_line.a

  scope = view.scope_name(point)
  if 'comment' in scope:
    point = view.extract_scope(point).a

  if 'string' in scope:
    for region in view.find_by_selector('string'):
      if region.a <= point and point <= region.b:
        point = region.a

  region = sublime.Region(view.line(point).a, point)
  new_line_text = view.substr(region)
  last_word = re.search(r'[$@\\]?[\w]+[?!]?(\.|->)?\s*$', new_line_text)
  if last_word != None:
    point = last_word.start(0) + region.a

  return point

def _shift_point_backward(view, point):
  region = sublime.Region(max(point - 32, 0), point)
  new_line_text = view.substr(region)
  last_word = re.search(r'[$@\\]?[\w]+[?!]?(\.|->)?\s*$', new_line_text)
  if last_word != None:
    point = last_word.start(0) + region.a

  return point

def _shift_point_forward(view, point):
  region = sublime.Region(point, min(point + 32, view.size()))
  new_line_text = view.substr(region)
  first_word = re.search(r'^\s*([$@]?[\w]+[?!]?)', new_line_text)
  if first_word != None:
    point = first_word.start(1) + region.a
  else:
    first_non_space = re.search(r'\S', new_line_text)
    if first_non_space != None:
      point = first_non_space.start(0) + region.a

  return point

def _join(view, tokens):
  if len(tokens) == 0:
    return tokens

  region = sublime.Region(tokens[0][0], tokens[-1][1])
  text = view.substr(region)

  index = 0
  while index < len(tokens) - 1:
    token = tokens[index]
    next_token = tokens[index + 1]
    delimeter = view.substr(sublime.Region(token[1], next_token[0]))
    stripped = delimeter.strip()

    join_required = (
      delimeter == '' or
      stripped == '::' or
      stripped == '\\' or
      stripped == '->' or (
        stripped == '.' and (delimeter[0] == '.' or delimeter[-1] == '.')
      )
    )

    if join_required:
      tokens[index : index + 2] = [[token[0], next_token[1]]]
    else:
      index += 1

  return tokens

def _parse(view, point, backward):
  state = _create_initial_state(view, point, backward)
  while True:
    if state.is_finished():
      break

    if len(state.matches) == 0:
      _advance(state)
      continue

    if _process_scope(state):
      continue

    if _process_nesting(state):
      continue

    match = state.matches[state.index]
    scope_name = state.view.scope_name(match.start(1) + state.region.a)
    if 'source' not in scope_name:
      state.finish()
      continue

    _expand_statement(state)
    if match.start(3) != -1:
      token = [match.start(3) + state.region.a, match.end(3) + state.region.a]

      first_char = match.group(3)[0]
      is_token = (first_char == '@' or
        first_char == '$' or (
        'control' not in scope_name and
        'operator' not in scope_name and
        'storage' not in scope_name
      ))

      if is_token:
        state.tokens.append(token)

    _advance(state)

  if backward:
    if len(state.tokens) > 0 and state.statement[1] > state.tokens[-1][0]:
      state.statement[1] = state.tokens[-1][0]
    state.tokens = list(reversed(state.tokens))
    state.statement = list(reversed(state.statement))
  else:
    if len(state.tokens) > 0 and state.statement[1] < state.tokens[-1][1]:
      state.statement[1] = state.tokens[-1][1]
  return state.tokens, state.statement

def _expand_statement(state):
  match = state.matches[state.index]
  if match.group(1) == None:
    return

  close = STATEMENT_KEYS[state.backward]['close']
  word = match.group(1).strip()

  if word != '' and word not in close:
    if state.backward:
      state.statement[1] = state.region.a + match.start(1)
    else:
      state.statement[1] = state.region.a + match.end(1)

def _create_initial_state(view, point, backward):
  region, text = _get_region_by_point(view, point, backward)
  matches = _get_matches(text, backward, PATTERN)
  state = State(view, region, text, backward, matches, [point, point])
  return state

def _process_scope(state):
  match = state.matches[state.index]
  point = match.start(1) + state.region.a

  scope_name = state.view.scope_name(point)
  if ' string' in scope_name:
    string = None
    for region in state.strings:
      if region.contains(point):
        string = region
        break

    if string == None:
      string = state.view.extract_scope(point)

    state.tokens.append([string.a, string.b])
    _ignore_region(state, string)
    return True
  elif 'comment' in scope_name:
    region = state.view.extract_scope(point)
    _ignore_region(state, region)
    return True

  return False

def _process_nesting(state):
  # ruby block call hack
  if _is_ruby_block(state):
    return True

  match = state.matches[state.index]
  if match.start(2) == -1:
    return False

  keychars = STATEMENT_KEYS[state.backward]
  if match.group(2) in keychars['close']:
    state.finish()
    return True

  region = _get_nesting_region(state, match.group(2))
  state.tokens.append([region.a, region.b])
  _ignore_region(state, region)
  return True

def _is_ruby_block(state):
  match = state.matches[state.index]

  if match.group(4) != '|':
    return False

  if state.backward:
    operator = re.search(r'{\s*(\|)', state.text)
    if operator != None and operator.start(1) == match.start(4):
      state.finish()
      return True

    operator = re.search(r',\s*\w+\s*(\|)\s*$', state.text)
    if operator != None and operator.start(1) == match.start(4):
      state.finish()
      return True
  else:
    operator = re.search(r',\s*\w+\s*(\|)\s*$', state.text)
    if operator != None and operator.start(1) == match.start(4):
      state.finish()
      return True

  return False

def _get_nesting_region(state, bracket):
  nesting = 1
  pattern = re.compile(re.escape(bracket) + '|' + re.escape(BRACKETS[bracket]))

  point = state.region.a
  if state.backward:
    point += state.matches[state.index].start(2)
  else:
    point += state.matches[state.index].end(2)

  region, text = _get_region_by_point(state.view, point, state.backward)

  shift = region.a
  matches = _get_matches(text, state.backward, pattern)

  while True:
    for match in matches:
      scope_name = state.view.scope_name(match.start(0) + shift)
      if ' string' in scope_name or ' comment' in scope_name:
        continue

      if match.group(0) == bracket:
        nesting += 1
        continue

      nesting -= 1
      if nesting == 0:
        if state.backward:
          end = state.matches[state.index].end(2) + state.region.a
          start = match.start(0) + shift
        else:
          start = state.matches[state.index].start(2) + state.region.a
          end = match.end(0) + shift

        return sublime.Region(start, end)

    region, text = _get_next_line(state.view, state.backward, region)

    if region == None:
      if state.backward:
        return sublime.Region(0, point)
      else:
        return sublime.Region(point, state.view.size())

    shift = region.a
    matches = _get_matches(text, state.backward, pattern)

def _ignore_region(state, region):
  point = None
  if state.backward:
    if region.a < state.region.a:
      point = region.a
  else:
    if region.b > state.region.b:
      point = region.b

  if point != None:
    region, text = _get_region_by_point(state.view, point, state.backward)
    matches = _get_matches(text, state.backward, PATTERN)
    state.set_region(region, text, matches)
  else:
    begin, end = region.begin(), region.end()

    while True:
      _advance(state)
      if state.is_finished():
        return

      token_point = state.region.a + state.matches[state.index].start(1)
      if token_point <= begin or end <= token_point:
        if state.backward:
          _advance(state)
        break

def _advance(state):
  if state.index == state.last_index or len(state.matches) == 0:
    _parse_next_region(state)
  else:
    state.index += 1

def _get_region_by_point(view, point, backward):
  line = view.line(point)
  if backward:
    region = sublime.Region(line.a, point)
  else:
    region = sublime.Region(point, line.b)

  return region, view.substr(region)

def _parse_next_region(state):
  region, text = _get_next_line(state.view, state.backward, state.region)
  if region == None:
    state.finish()
    return

  matches = _get_matches(text, state.backward, PATTERN)

  if _is_statement_end_found(state, region, matches):
    state.finish()
  else:
    state.set_region(region, text, matches)

def _is_statement_end_found(state, region, matches):
  if _get_lines_delimeter(state, matches) != '':
    return False

  match = len(matches) > 0 and matches[0] or None
  state_match = len(state.matches) > 0 and state.matches[-1] or None

  is_operator = ((
    match != None and
    match.start(3) != -1 and
    'operator' in state.view.scope_name(region.a + match.start(3)) and
    match.group(3) != '$' # $ is not operator (js case); sublime, even don't think about it
  ) or (
    state_match != None and
    state_match.start(3) != -1 and
    'operator' in state.view.scope_name(state.region.a +
      state_match.start(3)) and
    state_match.group(3) != '$' # $ is not operator (js case); sublime, even don't think about it
  ))

  if is_operator:
    return False

  return True

def _get_lines_delimeter(state, next_matches):
  delimeter = ''

  current = len(state.matches) > 0 and state.matches[-1].group(4) or None
  if current != None:
    current = current.strip()
    append = True

    if state.backward and current == '\\':
      append = False

    if current in STATEMENT_DELIMETERS:
      append = False

    if append:
      delimeter += current

  following = len(next_matches) > 0 and next_matches[0].group(4) or None
  if following != None:
    following = following.strip()
    if following not in STATEMENT_DELIMETERS:
      delimeter += following

  return delimeter

def _get_next_line(view, backward, line):
  result, text = _get_next_line_info(view, backward, line)

  while True:
    if result == None:
      break

    point = line.a + len(text) - len(text.lstrip())

    stripped = text.strip()
    is_comment_line = (
      'comment' in view.scope_name(point) and
      view.extract_scope(point).size() == len(stripped)
    )

    if text != None and stripped != '' and not is_comment_line:
      break

    result, text = _get_next_line_info(view, backward, result)

  return result, text

def _get_next_line_info(view, backward, line):
  if backward:
    if line.a == 0:
      return None, None
    line = view.line(line.a - 1)
  else:
    if line.b == view.size():
      return None, None
    line = view.line(line.b + 1)

  is_full_coment = (
    'comment' in view.scope_name(line.a) and
     view.extract_scope(line.a).contains(line)
  )

  if is_full_coment:
    return None, None

  text = view.substr(line)

  return line, text

def _get_matches(text, backward, pattern):
  matches = list(re.finditer(pattern, text))

  if backward:
    matches = list(reversed(matches))

  return matches