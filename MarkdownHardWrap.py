import sublime, sublime_plugin
import paragraph
import textwrap
import string
import re


class MarkdownWrapLinesCommand(paragraph.WrapLinesCommand):
    persistent_prefixes = re.compile("^\s*>\s+")
    initial_prefixes = re.compile("^\s*([-*+]|\d+\.)?\s+")

    def extract_prefix(self, sr):
        lines = self.view.split_by_newlines(sr)

        if len(lines) == 0:
            return None

        lineone = self.view.substr(lines[0])
        print "Line one: %s" % lineone
        persistent_prefix_match = self.persistent_prefixes.match(lineone)
        initial_prefix_match = self.initial_prefixes.match(lineone)
        print "Persistent prefix: %s" % persistent_prefix_match
        print "Initial prefix: %s" % initial_prefix_match

        if not initial_prefix_match and not persistent_prefix_match:
            return None

        prefix = self.view.substr(sublime.Region(lines[0].begin(),
            lines[0].begin() + initial_prefix_match.end()))

        print "Prefix: %s" % prefix

        if persistent_prefix_match:
            for line in lines[1:]:
                if self.view.substr(sublime.Region(line.begin(),
                        line.begin() + len(prefix))) != prefix:
                    return None
            return (prefix, prefix)
        return (prefix, re.sub('.', ' ', prefix))

    def run(self, edit, width=0):
        print "Running."
        for key in ["hard_wrap_width", "wrap_width"]:
            if width == 0 and self.view.settings().get(key):
                try:
                    width = int(self.view.settings().get(key))
                    print "Setting with %s" % key
                except TypeError:
                    pass

        if width == 0 and self.view.settings().get("rulers"):
            # try and guess the wrap width from the ruler, if any
            try:
                width = int(self.view.settings().get("rulers")[0])
            except ValueError:
                pass
            except TypeError:
                pass

        if width == 0:
            width = 78

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


#class AutoHardWrapLines(sublime_plugin.EventListener):
#    width = 0
#
#    def get_width(self, view):
#        if self.width:
#            return self.width
#        else:
#            width = 0
#            if view.settings().get("wrapwidth"):
#                try:
#                    width = int(view.settings().get("wrapwidth"))
#                except TypeError:
#                    pass
#
#            if view.settings().get("rulers"):
#                # try and guess the wrap width from the ruler, if any
#                try:
#                    width = int(view.settings().get("rulers")[0])
#                except ValueError:
#                    pass
#                except TypeError:
#                    pass
#
#            self.width = width or 78
#            return self.width
#
#    def on_modified(self, view):
#        if "Markdown" in view.settings().get('syntax'):
#            c = view.rowcol(view.sel()[-1].end())[1]
#            if c > (self.width or self.get_width(view)):
#                print "%s > %s" % (c, self.width)
#                view.run_command('markdown_wrap_lines')
