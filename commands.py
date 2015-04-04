import sublime
import sublime_plugin

import re

try:
  from Statement import statement
except ImportError:
  sublime.error_message("Dependency import failed; please read readme for " +
   "Statement plugin for installation instructions; to disable this " +
   "message remove this plugin")


regions_added = False

# class HighlightTokens(sublime_plugin.TextCommand):
#   def run(self, edit):
#     tokens, _ = parse(self.view, self.view.sel()[0].b)
#     regions = []
#     for token in tokens:
#       regions.append(sublime.Region(token[0], token[1]))
#     self.view.add_regions('tokens', regions, 'string', '', sublime.DRAW_EMPTY)

# class Listemer(sublime_plugin.EventListener):
#   def on_selection_modified_async(self, view):
#     view.run_command('show_tokens')

class HighlightStatement(sublime_plugin.TextCommand):
  def run(self, edit, root = False):
    if root:
      container = statement.get_root_statement(self.view, self.view.sel()[0].b)
    else:
      container = statement.get_statement(self.view, self.view.sel()[0].b)

    self.view.add_regions('statement_tokens', [sublime.Region(*container)],
      'string', '', sublime.DRAW_EMPTY | sublime.DRAW_OUTLINED)

class Base(sublime_plugin.TextCommand):

  def _run(self, callback, edit, as_arguments, *args):
    regions, selections = [], []

    for sel_index, sel in enumerate(self.view.sel()):
      tokens = self._get_tokens(sel, as_arguments)
      result = callback(sel_index, sel, tokens, edit, as_arguments, *args)

      if result == None:
        selections.append(sel)
        continue

      new_sel, new_tokens = result
      if new_sel == None:
        new_sel = sel

      if new_tokens == None:
        new_tokens = tokens

      selections.append(new_sel)
      regions += new_tokens

    self.view.sel().clear()
    self.view.sel().add_all(selections)

    self._highlight(regions)

  def _highlight(self, tokens):
    highlight = []
    for token in tokens:
      highlight.append(sublime.Region(token[0], token[1]))

    self.view.erase_regions('statement_token')
    self.view.add_regions('statement_tokens', highlight, 'string', '',
      sublime.DRAW_EMPTY | sublime.DRAW_OUTLINED)

    global regions_added
    regions_added = True

  def _get_tokens(self, sel, as_arguments):
    if as_arguments:
      tokens = statement.get_arguments(self.view, sel.a)
    else:
      tokens = statement.get_tokens(self.view, sel.a)

    return tokens

  def _get_position(self, tokens, sel, index, swap, position):
    token_index, result = self._get_position_for_index(tokens, sel, index, swap,
      position)

    if result == None:
      result = self._get_position_for_token(tokens[token_index], sel, position,
        swap)

    return token_index, result

  def _get_position_for_token(self, token, sel, position, swap):
    if position == 'start' or position == None:
      if token[0] == sel.b and swap:
        result = token[1]
      else:
        result = token[0]
    elif position == 'end':
      if token[1] == sel.b and swap:
        result = token[0]
      else:
        result = token[1]
    elif position == 'both':
      raise Exception('Can not use position "' + position + '" with given ' +
        'options')
    else:
      raise Exception('Unknown position "' + position + '"')

    return result

  def _get_position_for_index(self, tokens, sel, index, swap = False,
    position = None):

    new_index = self._prepare_index(tokens, index, sel)
    result = None
    if isinstance(index, str):
      current, _ = statement.get_token(self.view, sel.b, tokens)
      if index == 'next':
        positions = self._get_positions(tokens, position)
        result = positions[len(positions) - 1]
        for cursor in positions:
          if cursor > sel.b:
            result = cursor
            break

      elif index == 'previous':
        positions = self._get_positions(tokens, position)
        result = positions[0]
        for cursor in reversed(positions):
          if sel.b > cursor:
            result = cursor
            break
      elif index != 'current':
        raise Exception('Wrong index "' + index + '"')

    return new_index, result

  def _prepare_index(self, tokens, index, sel):
    if isinstance(index, str):
      current, _ = statement.get_token(self.view, sel.b, tokens)
      if index == 'current':
        return current
      elif index == 'next':
        index = current + 1
      elif index == 'previous':
        index = current - 1
      else:
        raise Exception('Wrong index "' + index + '"')

    if index > len(tokens) - 1:
      index = len(tokens) - 1

    if index < 0:
      index = 0

    return index

  def _get_positions(self, tokens, position):
    positions = []
    for token in tokens:
      if position == 'start' or position == None:
        positions.append(token[0])
      if position == 'end' or position == None:
        positions.append(token[1])

      if position != None and position not in ['start', 'end']:
        raise Exception('Unknown position "' + position + '"')

    return positions

  def _get_selection(self, tokens, sel, index, select, position):
    if index > len(tokens) - 1 or index < 0:
      return sel

    token = tokens[index]
    if select:
      return sublime.Region(token[0], token[1])

    return sublime.Region(position, position)

class DuplicateStatement(sublime_plugin.TextCommand):
  def run(self, edit):
    for sel in self.view.sel():
      self._duplicate(edit, sel)

  def _duplicate(self, edit, sel):
    container = statement.get_root_statement(self.view, sel.b)
    if container == None:
      return

    line = self.view.line(container[0])
    if self.view.substr(sublime.Region(line.a, container[0])).strip() != '':
      return

    container[0] = line.a
    value = self.view.substr(sublime.Region(*container))
    self.view.insert(edit, container[0], value + "\n")

class AddLineAfterStatement(sublime_plugin.TextCommand):
  def run(self, edit, before = False):
    sels = []
    for sel in reversed(self.view.sel()):
      point = self._add_line(edit, sel, before)
      self.view.insert(edit, point, "\n")
      if not before:
        point += 1
      sels.append(sublime.Region(point, point))

    self.view.sel().clear()
    self.view.sel().add_all(sels)
    self.view.run_command('reindent')

  def _add_line(self, edit, sel, before):
    container = statement.get_root_statement(self.view, sel.b)
    if container == None:
      return

    if before:
      line = self.view.line(container[0])
      if self.view.substr(sublime.Region(line.a, container[0])).strip() != '':
        return
      point = line.a
    else:
      line = self.view.line(container[1])
      if self.view.substr(sublime.Region(line.b, container[1])).strip() != '':
        return
      point = line.b

    return point

class HighlightTokens(Base):
  def run(self, edit, as_arguments = False, index = 'current'):
    self._run(self._execute, edit, as_arguments, index)

  def _execute(self, sel_index, sel, tokens, edit, as_arguments, index):
    return sel, tokens

class DeleteRootStatement(Base):
  def run(self, edit):
    for sel in reversed(self.view.sel()):
      self._delete_root_statement(edit, sel)

  def _delete_root_statement(self, edit, sel):
    container = statement.get_root_statement(self.view, sel.b)
    line = self.view.line(container[0])

    if self.view.substr(sublime.Region(line.a, container[0])).strip() == '':
      container[0] = line.a

    if self.view.substr(sublime.Region(container[1], line.b)).strip() == '':
      container[1] = line.b + 1

    self.view.erase(edit, sublime.Region(*container))

class DeleteToken(Base):

  def run(self, edit, index = 'current', as_arguments = False):
    self._run(self._execute, edit, as_arguments, index)

  def _execute(self, sel_index, sel, tokens, edit, as_arguments, index):
    if len(tokens) == 0:
      container = statement.get_parent_token(self.view, sel.b)
      if container != None:
        tokens = statement.get_tokens(self.view, container[0])
        if len(tokens) == 0:
          return sel, []

        token_index, cursor = self._get_position(tokens, sel, index, False,
          None)

      if len(tokens) == 0:
        return sel, []

    else:
      token_index, cursor = self._get_position(tokens, sel, index, False, None)

    region = statement.get_token_delete_region(self.view, sel.b, tokens)
    self.view.replace(edit, region, '')

    sel = self.view.sel()[sel_index]
    tokens = self._get_tokens(sel, as_arguments)

    # if index == len(tokens) - 1:
    sel = self._get_selection(tokens, sel, token_index, False, cursor)

    return sel, tokens

class SelectCurrentToken(Base):
  def run(self, edit, as_arguments = False):
    selections = []
    for sel in self.view.sel():
      selections.append(self._get_new_selection(sel, as_arguments))

    self.view.sel().clear()
    self.view.sel().add_all(selections)

  def _get_new_selection(self, sel, as_arguments = False):
    token = None
    if not as_arguments:
      _, token = statement.get_token(self.view, sel.b)

    if token == None or (sel.begin() <= token[0] and token[1] <= sel.end()):
      _, token = statement.get_argument(self.view, sel.b)

    if token == None or (sel.begin() <= token[0] and token[1] <= sel.end()):
      _, token = statement.get_assignment(self.view, sel.b)

    if token == None or (sel.begin() <= token[0] and token[1] <= sel.end()):
      tokens = statement.get_tokens(self.view, sel.b)
      if len(tokens) > 0:
        token = [tokens[0][0], tokens[-1][1]]

    if token == None or (sel.begin() <= token[0] and token[1] <= sel.end()):
      token = statement.get_statement(self.view, sel.b)

    if token == None or (sel.begin() <= token[0] and token[1] <= sel.end()):
      token = statement.get_parent_token(self.view, sel.b)

    if token == None:
      token = [sel.begin(), sel.end()]

    return sublime.Region(token[0], token[1])

class SelectCurrentTokenTail(SelectCurrentToken):
  def run(self, edit, as_arguments = False):
    selections = []
    for sel in self.view.sel():
      new_sel = self._get_new_selection(sel, as_arguments)
      if new_sel.a < new_sel.b:
        new_sel.a = sel.begin()
      else:
        new_sel.b = sel.begin()

      selections.append(new_sel)

    self.view.sel().clear()
    self.view.sel().add_all(selections)


class SelectRootStatement(Base):
  def run(self, edit):
    selections = []
    for sel in self.view.sel():
      selections.append(self._get_new_selection(sel))

    self.view.sel().clear()
    self.view.sel().add_all(selections)

  def _get_new_selection(self, sel):
    container = statement.get_root_statement(self.view, sel.b)
    if container == None:
      return

    tokens = statement.get_tokens(self.view, container[0])
    if tokens == None:
      return

    selection = [tokens[0][0], tokens[-1][1]]
    if sel.begin() <= selection[0] and selection[1] <= sel.end():
      selection = container

    return sublime.Region(*selection)

class GotoToken(Base):
  def run(self, edit, index = 'current', as_arguments = False, select = False,
    swap = False, position = None):

    self._run(self._execute, edit, as_arguments, index, select, swap, position)

  def _execute(self, _1, sel, tokens, _2, as_arguments, index, select, swap,
    position):

    if len(tokens) == 0:
      return

    token_index, cursor = self._get_position(tokens, sel, index, swap, position)
    sel = self._get_selection(tokens, sel, token_index, select, cursor)
    index, _ = statement.get_token(self.view, cursor, tokens)

    if index != None:
      tokens.pop(index)

    return sel, tokens

class SwapTokens(Base):
  def run(self, edit, as_arguments = False, source = 'current', target = 0):
    self._run(self._execute, edit, as_arguments, source, target)

  def _execute(self, _, sel, tokens, edit, as_arguments, source, target):
    source_index = self._prepare_index(tokens, source, sel)
    target_index = self._prepare_index(tokens, target, sel)

    exit = (source_index == target_index or source_index == None or
      target_index == None)

    if exit:
      return None, None

    source_token = tokens[source_index]
    target_token = tokens[target_index]

    sel_shift = [sel.a - source_token[0], sel.b - source_token[0]]

    source_token_region = sublime.Region(source_token[0], source_token[1])
    source_token_value = self.view.substr(source_token_region)

    target_token_region = sublime.Region(target_token[0], target_token[1])
    target_token_value = self.view.substr(target_token_region)

    self.view.add_regions('statement_target_token', [target_token_region])

    self.view.replace(edit, source_token_region, target_token_value)
    self.view.replace(edit, self.view.get_regions('statement_target_token')[0],
      source_token_value)

    self.view.erase_regions('statement_target_token')

    parse_position = min(source_token[0], target_token[0])
    parse_region = sublime.Region(parse_position, parse_position)
    tokens = self._get_tokens(parse_region, as_arguments)
    new_source_token = tokens[target_index]

    cursor = sublime.Region(new_source_token[0] + sel_shift[0],
      new_source_token[0] + sel_shift[1])

    tokens.pop(target_index)

    return cursor, tokens

class Listener(sublime_plugin.EventListener):
  def on_selection_modified_async(self, view):
    global regions_added
    if regions_added:
      regions_added = False
      return

    view.erase_regions('statement_tokens')