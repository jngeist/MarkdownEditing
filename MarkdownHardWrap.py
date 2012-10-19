import sublime, sublime_plugin
import paragraph
import textwrap
import string
import re


def get_width(view):
    width = 0
    for key in ["hard_wrap_width", "wrap_width"]:
        if width == 0 and view.settings().get(key):
            try:
                width = int(view.settings().get(key))
            except TypeError:
                pass

    if width == 0 and view.settings().get("rulers"):
        # try and guess the wrap width from the ruler, if any
        try:
            width = int(view.settings().get("rulers")[0])
        except ValueError:
            pass
        except TypeError:
            pass

    if width == 0:
        width = 78

    return width


class MarkdownWrapLinesCommand(paragraph.WrapLinesCommand):
    persistent_prefixes = re.compile("^\s*(>\s+)+")
    initial_prefixes = re.compile("^\s*([-*+]|\d+\.)?\s+")

    def extract_prefix(self, sr):
        lines = self.view.split_by_newlines(sr)

        if len(lines) == 0:
            return None

        lineone = self.view.substr(lines[0])
        prefix_match = self.persistent_prefixes.match(lineone)
        if prefix_match:
            prefix_type = 'persistent'
        else:
            prefix_match = self.initial_prefixes.match(lineone)
            prefix_type = 'initial'

        if not prefix_match:
            return None

        prefix = self.view.substr(sublime.Region(lines[0].begin(),
            lines[0].begin() + prefix_match.end()))

        if prefix_type == 'persistent':
            for line in lines[1:]:
                if self.view.substr(sublime.Region(line.begin(),
                        line.begin() + len(prefix))) != prefix:
                    return None
            return (prefix, prefix)
        return (prefix, re.sub('.', ' ', prefix))

    def run(self, edit, width=0):
        width = get_width(self.view)
        # Make sure tabs are handled as per the current buffer
        tab_width = 8
        if self.view.settings().get("tab_size"):
            try:
                tab_width = int(self.view.settings().get("tab_size"))
            except TypeError:
                pass

        if tab_width == 0:
            tab_width == 8

        paragraphs = []
        for s in self.view.sel():
            paragraphs.extend(paragraph.all_paragraphs_intersecting_selection(self.view, s))

        if len(paragraphs) > 0:
            self.view.sel().clear()
            for p in paragraphs:
                self.view.sel().add(p)

            # This isn't an ideal way to do it, as we loose the position of the
            # cursor within the paragraph: hence why the paragraph is selected
            # at the end.
            for s in self.view.sel():
                wrapper = textwrap.TextWrapper()
                wrapper.expand_tabs = False
                wrapper.width = width
                prefix = self.extract_prefix(s)
                if prefix:
                    wrapper.initial_indent = prefix[0]
                    wrapper.subsequent_indent = prefix[1]
                    wrapper.width -= self.width_in_spaces(prefix, tab_width)

                if wrapper.width < 0:
                    continue

                txt = self.view.substr(s)
                if prefix:
                    txt = txt.replace(prefix[0], u"")

                txt = string.expandtabs(txt, tab_width)

                txt = wrapper.fill(txt) + u"\n"
                self.view.replace(edit, s, txt)

            # It's unhelpful to have the entire paragraph selected, just leave the
            # selection at the end
            ends = [s.end() - 1 for s in self.view.sel()]
            self.view.sel().clear()
            for pt in ends:
                self.view.sel().add(sublime.Region(pt))


class AutoHardWrapLines(sublime_plugin.EventListener):
    TARGET_SETTINGS = ['hard_wrap_lines', 'hard_wrap_width', 'wrap_width', 'ruler']
    width = 0
    callback_is_registered = False

    def _add_callback(self, view):
        s = view.settings()
        for key in self.TARGET_SETTINGS:
            s.add_on_change(key, lambda: self._update_width(view))

    def active(self, view):
        s = view.settings()
        return (
            "Markdown" in s.get('syntax') and
            s.get('hard_wrap_lines')
        )

    def _update_width(self, view):
        self.width = get_width(view)

    def on_activated(self, view):
        if "Markdown" in view.settings().get('syntax'):
            if not self.callback_is_registered:
                self._add_callback(view)

    def on_modified(self, view):
        if self.active(view):
            c = view.rowcol(view.sel()[-1].end())[1]
            if c > self.width:
                view.run_command('markdown_wrap_lines')
