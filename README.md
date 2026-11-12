# Novelshop

A plain, focused writing app in Python + PySide6 (Qt). File tree, editor,
word count, autosave — in its own light or dark theme, with a frameless
window styled like a native app.

![Novelshop — the binder on the left, a scene in the editor](screenshot.png)

## How to run it

1. Open this folder in PyCharm (File → Open, pick the `novel-shop` folder).
2. Install the dependency: `pip install -r requirements.txt`
   (PyCharm can do this for you from the requirements file, or run it in
   the built-in terminal.)
3. Run `main.py` (or the ▶ button next to `main()`).

### Piper voice (for the neural Read Aloud voice)

Two one-time steps, only if you want the Piper voice instead of the
system voices. `piper-tts` is in `requirements.txt` (step 2 installs
it), so this is just the voice itself:

1. Download a voice — two files, the model and its config. A good
   one to start with is lessac (a natural-sounding American voice):
   `en_US-lessac-medium.onnx` and `en_US-lessac-medium.onnx.json`,
   from <https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium>.
   Put them together in a folder (they are about 63MB).
2. In the app: View → Read Aloud Voice → Piper (neural), then
   Choose Piper voice file... and pick the `.onnx`. The app remembers
   the voice.

## What it does

- **Open Folder** (Ctrl+Shift+O) — the file tree on the left lists the
  folder's `.txt` and `.md` files. Click one to open it.
- **Editor** — write in the main pane. Word, character, and line counts
  plus line/column live in the status bar.
- **Save** (Ctrl+S) / **Save As** (Ctrl+Shift+S) / **New** (Ctrl+N) /
  **Open File** (Ctrl+O).
- **Autosave** — 2 seconds after you stop typing, if the document has a
  file. Untitled documents are never autosaved anywhere.
- **Dirty tracking** — a `*` in the title while there are unsaved changes,
  and a Save / Don't save / Cancel prompt before New, Open, or Quit would
  discard them.
- **Look** — the app has its own light and dark themes, a frameless
  window, and a 38px menu bar as its top bar (see "Novelshop themes"
  below). The editor font (Georgia 15px) is set on the editor itself.
- **Tabs** — each document opens in its own tab. Clicking a file that's
  already open switches to its tab instead of opening it twice. Close a
  tab with its × button or Ctrl+W; dirty tabs ask before closing.
- **Binder** — the file tree starts empty. Open a folder (Ctrl+Shift+O)
  and its files appear grouped under section headers that only exist
  when files of that type are in the folder: Parts (`.part`), Chapters
  (`.chapter`), Scenes (`.scene`), Drafts (`.draft`), Plot (`.plot`),
  Outlines (`.outline`), Characters (`.character`), Locations
  (`.location`), Languages (`.language`), Cultures (`.culture`),
  Factions (`.faction`), Species (`.species`), Magic (`.magic`), Items
  (`.item`), Timelines (`.timeline`), Glossaries (`.glossary`),
  Research (`.research`), Notes (`.note`), and Documents (`.txt`,
  `.md`). Any other extension works too: a `.spell` file gets its own
  "Spell" section. Every file is plain text; the extension is what
  categorizes it. Files stay where they are on disk — only the tree
  groups them. Headers are spacers, not folders: bold text, no folder
  icon, and each section collapses with its arrow; sections open
  expanded by default, and one you closed by hand stays closed. Each
  file has a badge icon: a colored square with two letters for its
  type (Ch for chapter, Sc for scene, Ca for character), and a custom
  extension gets a grey badge from its own letters. File → New File...
  opens a window where you name the file and pick its type from a
  dropdown (Custom is an option there). The folder picker lists the
  folder's text files, so a folder never looks empty.
- **Rename** — right-click a file in the tree (or press F2 with it
  selected) to rename it, name and type. The window is pre-filled
  with what the file is now; change the name, or pick a different
  type from the dropdown. A new name that already exists is refused,
  and so is a name Windows won't allow. Changing the type moves the
  file to that section — a `.txt` note becomes a `.plot`, a `.draft`
  becomes a `.chapter` — and if the file is open in a tab, the tab
  follows it to the new name, unsaved changes included. Snapshots
  need nothing: they are timestamp-named in the folder's
  `.snapshots`, not named after the file.
- **Trash** — right-click a file in the tree (or press Delete with it
  selected) to move it to a `.trash` folder inside the project, where
  it shows up under a Trash section at the bottom of the tree. No
  confirmation: it is recoverable, so deleting is one click. A file
  deleted twice, or restored over an existing file, gets a number
  ("Chapter 1 2.chapter") so nothing is overwritten. Right-click a
  trashed file to Restore it, or Delete Permanently; right-click the
  Trash header to Empty Trash. The permanent deletes ask first —
  they can't be undone. If the file is open in a tab, the tab closes
  first, and a dirty tab asks to save so the trashed copy is up to
  date. The Trash folder travels with the project, and it is hidden
  from the tree like any other dot-folder.
- **Find & replace** — Ctrl+F opens a Find bar under the tabs (Ctrl+H
  jumps straight to the Replace field). Find Next/Previous wrap around
  the document, Replace acts on the current match, Replace All reports
  how many it replaced, Aa toggles case sensitivity, Esc closes the bar.
  It always searches the tab you're looking at.
- **Snapshots** — File → Take Snapshot (Ctrl+Shift+T) saves a dated
  backup of the current document in a `.snapshots` folder next to it.
  File → Snapshots... lists them newest first; Restore loads one back
  into the editor as unsaved changes (Ctrl+Z undoes it, nothing is
  written until you save), Delete removes it. **Compare** shows what
  changed: select two snapshots to diff them, or one to diff it
  against the current document — added lines in green, removed in
  red.
- **Quick Open** — File → Quick Open... (Ctrl+P) jumps to any file in
  the folder by typing its name. Type a few letters and the list
  narrows; Enter or a double-click opens the file.
- **Session restore** — on quit it remembers the open folder and all
  open files, and reopens them on launch, so you pick up where you
  left off. With no session yet, the file tree stays empty until you
  open a folder (Ctrl+Shift+O, which starts in Documents).
- **Export** — File → Export... (Ctrl+E) turns the folder into a
  finished manuscript: DOCX (Word), EPUB (ebook), or PDF. It stitches
  the files together in tree order, each file's name becoming its
  heading, parts and chapters starting on a new page. Parts, chapters,
  and scenes are ticked by default; character sheets, notes, and other
  reference files are left out unless you tick them in. Title defaults
  to the folder name; author is optional. Unsaved changes are saved
  first, so nothing is missed. DOCX needs python-docx, EPUB needs
  ebooklib (both in `requirements.txt`); PDF uses Qt's own printing.
- **Rich text** — the editor reads and writes Markdown, so the files
  stay plain text: `**bold**`, `*italic*`, `<u>underlined</u>`,
  `~~struck~~`, and `==highlighted==` in the file, rendered formatted
  in the editor. Bold (Ctrl+B), Italic (Ctrl+I), Underline (Ctrl+U),
  Strikethrough (Ctrl+Shift+X), and Highlight (Ctrl+Shift+H, pale
  yellow, for passages to come back to) buttons sit in the formatting
  toolbar, and they apply to whatever is selected; clicking a button
  again turns its formatting off. Ctrl+Space still takes the selection
  back to plain text in one go. The toolbar also has the font picker
  and size: that's the writing font for the whole editor, remembered
  between runs (a font can't live in a Markdown file, so it's a
  preference, not part of the document). Bold, italic, underline,
  strikethrough, and highlight survive into the export — they stay
  that way in the DOCX, EPUB, and PDF.
- **Headings, scene breaks, and block quotes** — a line starting with
  `# ` is a heading and `## ` a subheading: it renders larger and bold
  in the editor (the markers fade to grey), and exports as a real
  heading. Edit → Insert → Heading (Ctrl+1) and Subheading (Ctrl+2)
  put the markers at the start of the current paragraph, or take them
  off again. Edit → Insert → Scene Break (Ctrl+Shift+Return) drops a
  centered `***` on its own line, ready for the next scene; a line
  that is just `***` is always centered in the editor and in the
  export. Edit → Insert → Block Quote turns the current paragraph
  into a `> ` quotation — a letter, a diary entry, an epigraph —
  shown italic in the editor with the marker faded, and exported as
  a real block quotation (indented and italic).
- **Line spacing, typewriter scrolling, first-line indent** — Format →
  Line Spacing offers Single, 1.5 Lines, and Double, for readability
  while drafting. Format → Typewriter Scrolling keeps the line being
  typed centered on screen. Format → First-Line Indent gives each
  paragraph the traditional novel indent (wrapped lines stay at the
  left edge). All three are display-only preferences, remembered
  between runs; the file stays plain Markdown.
- **Text alignment** — Format → Align sets the current paragraph Left
  (Ctrl+L), Center (Ctrl+E), Right (Ctrl+R), or Justify (Ctrl+J).
  Justify is how novels are printed; center is for titles and
  epigraphs. The alignment is stored in the file as an HTML div, so
  it survives a reload and reaches the export.
- **Editing moves** — Ctrl+D duplicates the current paragraph below
  itself; Alt+Up and Alt+Down move the current paragraph up or down,
  swapping it with its neighbor (the cursor follows the moved
  paragraph). Format → Change Case turns a selection — or the word under
  the cursor — into UPPERCASE, lowercase, Title Case, or Sentence
  case. Ctrl+Shift+V pastes the clipboard as plain text, without the
  fonts and colors a paste from the web would bring in.
- **Regex find** — the find bar's `.*` toggle treats the find text as
  a regular expression: find ` {2,}` for double spaces, `\d{3}-\d{4}`
  for phone numbers, and Replace All takes `\1`, `\2` backreferences
  in the replacement. An invalid pattern says so instead of failing.
- **Show invisibles** — Format → Show Invisibles ¶ shows spaces as
  dots, tabs as arrows, and paragraph and line breaks as marks, like
  Word's ¶ button, for spotting double spaces and stray blank lines.
  Display only, remembered between runs.
- **Zoom** — Ctrl+= enlarges the text a step, Ctrl+- shrinks it, and
  Ctrl+0 goes back to the saved writing font size. Display only.
- **Selection word count** — the status bar shows the selected text's
  word count alongside the document total, like Word does.
- **Go to Heading** — Edit → Go to Heading... (Ctrl+Shift+G) lists the
  document's `# ` and `## ` headings; pick one and the cursor jumps
  to it. For long chapters, faster than Go to Line.
- **Split File at Cursor** — Edit → Split File at Cursor splits the
  current file into two at the paragraph the cursor is in: the text
  before stays in the current file, the text from that paragraph on
  becomes a new file, named in a dialog (same type as the current
  file). Both are saved and the new file opens in a tab.
- **Merge Files** — Edit → Merge Files... is the counterpart to
  splitting: pick another file and its text is appended to the
  current one (after a blank line), the current file is saved, and
  the merged file is moved to the Trash, recoverable with Restore
  like any deleted file.
- **Join Paragraph** — Edit → Join Paragraph (Ctrl+Shift+J) joins the
  current paragraph with the next one, putting a space where the
  break was.
- **Select All Occurrences** — Edit → Select All Occurrences
  (Ctrl+Shift+L) selects every whole-word, case-sensitive occurrence
  of the word under the cursor and edits them all together, VS Code
  style: the first character typed replaces them all, later ones
  append, Backspace trims, and Escape, Enter, an arrow key, or a
  click ends it. One undo step per keystroke. Good for renaming a
  character in a chapter.
- **Auto-Capitalize Sentences** — as you type, the first letter of a
  sentence is capitalized. On by default; Format → Auto-Capitalize
  Sentences turns it off. It does not capitalize after an
  abbreviation (Mr., Dr., etc.).
- **Continue Lists on Enter** — Enter on a `- `, `* `, or numbered
  (`1. `, `2) `) item starts the next one, with the next number for
  ordered lists; an empty item loses its marker and the list ends.
  On by default; Format → Continue Lists on Enter turns it off.
- **Bookmark** — Edit → Toggle Bookmark (Ctrl+F2) marks the cursor's
  spot in the current file (one per file, remembered between runs;
  the marked line gets a faint mark), and Edit → Go to Bookmark
  (Shift+F2) jumps back to it. Toggling again at the same spot
  clears it. Lighter than a comment for "come back here".
- **Focus Sentence** — Format → Focus Sentence dims everything except
  the sentence being written, iA Writer style, so the eyes stay on
  the one sentence. Display only, remembered between runs. The dim
  marks share the editor's mark list with comment anchors and find
  matches, so they never clobber each other.
- **Line Numbers** — Format → Line Numbers shows a line-number margin
  on the left of the editor, in the file's logical lines (the same
  rows Go to Line counts: a paragraph break and a single newline
  inside a paragraph both start a new row, a wrapped line does not).
  Display only, remembered between runs.
- **Whole word + highlight all in find** — the find bar has a W
  toggle (find "cat" without matching "catalogue") and highlights
  every match in the document at once in translucent blue, with the
  current match as the solid selection. The marks clear when the bar
  hides.
- **Replace in Selection** — the find bar's Replace in Selection
  button replaces every match inside the selected text only, as one
  undoable edit. Good for renaming a character in one scene without
  touching the rest of the chapter. It refuses with "Select some text
  first" when nothing is selected.
- **Copy as Plain Text** — Edit → Copy as Plain Text copies the
  selection to the clipboard without the Markdown markers (**bold**,
  *italic*, ==highlight==, ~~strike~~, # headings, > quotes, <u>),
  so pasting into email or chat gives clean text.
- **Comments** — Edit → Comments… (Ctrl+Shift+C) pins a note to the
  selected passage ("fix this scene", "check the timeline") without
  changing the text. Commented passages get a light blue mark in the
  editor; the dialog lists the file's notes, jumps to a passage, and
  edits or deletes them. Notes live in a sidecar file next to the
  document (`Chapter 1.comments.json`), so the story file stays plain
  text and the notes travel with the project. A note whose passage was
  rewritten stays listed, marked as orphaned.
- **Entity highlighting** — like a code editor's syntax highlighting:
  when a character, spell, place, or other defined thing is mentioned
  in the text, its name is drawn in that category's color. The name
  comes from the file: `Aldric.character` makes "Aldric" a term,
  `Fireball.magic` makes "Fireball" one, and a custom `.spell` file
  works the same way. Matches are whole words, case-sensitive, so
  "Aldric" lights up but "aldric" and "Aldricson" don't. Format →
  Highlight Colors... picks the color for each category, or turns a
  category off. The colors are a display aid only — they are never
  written into the file.
- **Find in Project** — Edit → Find in Project... (Ctrl+Shift+F)
  searches every file in the open folder, not just the one you're
  looking at. Results list the file, the line, and the matching text;
  click one (or press Enter) and the file opens with that match
  selected. Aa toggles case sensitivity. Unsaved changes are saved
  first, so the search sees the current text. The window stays open
  while you work through the results. **Replace All** replaces the
  search text in every matching file at once: it counts first and
  asks ("Replace 5 matches in 3 files?") because it writes to every
  matching file and can't be undone in the editor. Any open tabs
  reload to show the new text.
- **Split View** — View → Split View (Ctrl+\) opens a second editor
  beside the tabs, for a reference file (a character sheet, a plot
  outline) while you write. Right-click a file in the tree → Open in
  Split, or toggle the view and pick one. The split file is editable
  and autosaves like a tab; closing the split with unsaved edits
  asks first. Bold, italic, underline, find, and read aloud act on
  whichever editor has the focus. Focus mode hides the split and
  brings it back after. The split file is not kept between runs —
  reopen it from the tree.
- **Manuscript view** — View → Manuscript (Ctrl+Shift+M) reads the
  whole book as one continuous document, in tree order, each file
  under its name as a heading — the same files and order as the
  export. Read-only, and the window stays open while you write;
  Refresh re-reads the files. For proofreading end to end, without
  exporting.
- **Read Aloud** — View → Read Aloud (Ctrl+Shift+R) reads the
  selected text (or the whole document, if nothing is selected)
  aloud. Toggle it again to stop; it stops by itself when it
  finishes. There are two voices to choose from, under View →
  Read Aloud Voice: **System voices** (the default) reads through
  the system's own voices — on Windows that is the built-in Windows
  voices, nothing to install and no internet. **Piper (neural)** is
  a local neural voice that sounds much more human; it needs two
  one-time steps (see "Piper voice" below), then it reads
  sentence by sentence, so it starts almost at once. If the system
  has no speech voices, it says so instead of speaking.
- **Spellcheck** — misspelled words get a red wavy underline as you
  type. Right-click one for suggestions, or "Add to dictionary" to
  stop flagging it. Character and spell names from your files are
  never flagged, and neither are acronyms like NASA. View →
  Spellcheck turns it on or off. It needs the pyspellchecker package
  (in `requirements.txt`); without it the app starts as normal and
  the Spellcheck menu item is greyed out.
- **Dictionary and thesaurus** — right-click any word for a Synonyms
  submenu (click one and it replaces the word) and a "Define 'word'"
  action that opens a dialog with the definitions by part of speech,
  an example, and the synonyms and antonyms for each sense. There is
  also a **Dictionary** button in the toolbar, for general searches:
  it opens a lookup window that stays open, with a search box — type
  any word and hit Enter. It is standalone, not tied to the editor:
  the box starts empty and looking a word up never touches your
  text. Synonyms in it are links, so clicking one looks that word
  up. Tick **Reverse search** in that window to describe a word
  instead of typing it ("a fear of heights") — it lists the words
  whose definitions match, and clicking one looks it up. The
  reverse search works best for short descriptions whose words
  appear in a definition; a natural sentence whose wording differs
  from the definition will not match. The words come from WordNet,
  offline: it needs the `wn` package (in `requirements.txt`) and a
  one-time data download, `python -m wn download ewn:2020` (about
  14MB), after which lookups work with no internet. Without the
  data, Define is greyed out and there is no Synonyms submenu — the
  app still starts as normal. The reverse index is built the first
  time you use it (a few seconds), then it is instant.
- **Focus Mode** — View → Focus Mode (F11) hides the file tree, the
  formatting toolbar, and the menus, and centers the page with wide
  margins. Just the writing. F11 or Esc leaves it; the toolbar comes
  back however you had it. Keyboard shortcuts (Ctrl+B, Ctrl+I,
  Ctrl+U, Ctrl+Space) still work while you're in it.
- **Overused Words** — Format → Overused Words underlines filler words
  like "very", "just", "really", and "suddenly" with a dotted orange
  line, so you can spot them and tighten the prose. It is a display
  aid only — nothing is written into the file. Turn it off from the
  same menu item.
- **Readability** — View → Readability... shows the current
  document's Flesch-Kincaid grade and reading-ease score, with the
  two averages that drive them (words per sentence, syllables per
  word). The window stays open while you write; Refresh re-reads
  the document. It is a rough gauge — it only measures sentence
  length and word length, not whether the writing is clear or good.
- **Find all mentions** — right-click any word in the editor →
  "Find all mentions of 'word'" opens Find in Project with that
  word, case-sensitive, so a name matches only itself. Click a
  result to jump to it. Good for consistency checks across the
  whole book.
- **Go to Line** — Edit → Go to Line... (Ctrl+G) jumps to a line
  number in the document you are working in.
- **Smart Quotes** — Format → Smart Quotes (on by default) turns
  straight quotes into curly ones as you type ("..." becomes
  "..."), "don't" gets a proper apostrophe, and "--" becomes an em
  dash (—). A hyphen inside a word ("well-known") is left alone.
  Format → Fix Typography does the same to the text you already
  have — the selection, or the whole document if nothing is
  selected — in one undo step, keeping bold and italic intact.
- **Project Word Count** — View → Project Word Count... lists every
  story file (parts, chapters, scenes) with its word count, and a
  total for the whole book at the bottom. Reference files (character
  sheets, notes) are left out. Just a total, no target. The window
  stays open while you write; Refresh saves unsaved edits and
  recounts.
- **Word counts in the tree** — every file in the binder shows its
  word count in a column next to its name, so chapter lengths are
  visible at a glance. Counts are cached by file, so only changed
  files are re-read.
- **Next / Previous File** — View → Next File (Ctrl+PageDown) and
  Previous File (Ctrl+PageUp) move through the files in tree order,
  wrapping at the ends, for reading a draft straight through.
- **Duplicate file** — right-click a file → Duplicate makes a
  "<name> copy" of it and opens it in a tab, for trying a rewrite
  without losing the original. Its comments sidecar comes along.
- **Project Spellcheck** — View → Project Spellcheck... lists every
  misspelled word in the whole project, most frequent first, with
  the files each appears in. It uses the same rules as the editor
  (your own words and entity terms are never flagged). Double-click
  a word to jump to its first occurrence.
- **Word Frequency** — View → Word Frequency... lists the book's
  most-used words (top 50) with counts and percentages. Common
  function words (the, and, of) are left out, so it surfaces the
  words you lean on. A filter box narrows the list.
- **Recent Folders** — File → Recent Folders lists the last five
  project folders, newest first, for switching between books in
  one click.
- **Back Up Project** — File → Back Up Project... zips the whole
  project folder (documents, snapshots, and Trash) to a location
  you pick, a safety net for the book.
- **Export Current File** — File → Export Current File... exports
  only the document you are working in, instead of the whole
  folder. The same dialog (format, title, author), with just this
  one file in it — ticked, whatever its type — and the title
  defaulting to the file's name. A file that was never saved has
  nothing on disk to export, so it asks to be saved first.
- **Novelshop themes** — View → Theme offers two of the app's own:
  **Novelshop Dark** is a flat dark theme: near-black panels
  (#0e0e0f background, #141415 chrome, #1a1a1c cards), near-white
  text, and a solid blue (#1a73e8) for selections, the active tab,
  and primary buttons, and the editor is near-black too, so the
  look holds while you write, including in Focus Mode.
  **Novelshop Light** is the same design inverted: a white writing
  surface, light grey chrome (#f0f0f0), near-black text, and the
  same blue accent. The menu bar is 38px tall with matching spacing
  between its items (File, Edit, Format, View...), and the items in
  the drop-down menus get the rounded bubble highlight on hover, and
  every button and input in the app is rounded the same way. The
  menu items sit vertically centered in the bar (they were glued to
  the top until the item padding was made tall enough to fill it),
  and the menus themselves have no border, just rounded corners.
  The font picker
  shows a drop-down arrow, and the font size is readable. The choice
  is remembered between runs (a saved "system" theme becomes Light). The editor's font and the entity
  highlight colors are separate preferences and are not touched by
  the theme. Polish: the frameless window gets a native drop shadow
  on Windows (CS_DROPSHADOW), the scrollbars are thin and rounded,
  the active tab is marked with a blue top edge, primary (default)
  buttons are solid blue, and the tree's rows have room to breathe.
- **Format menu** — the top bar has five menus (File, Edit, Format,
  View, Help). Format holds everything that changes how the writing looks
  or is typed: Align, Change Case, Line Spacing, Typewriter
  Scrolling, First-Line Indent, Show Invisibles, Focus Sentence,
  Line Numbers, Smart Quotes, Auto-Capitalize Sentences, Continue
  Lists on Enter, Fix Typography, Highlight Colors, Overused Words,
  and the Formatting Toolbar toggle. View keeps the app's
  appearance (Theme), the analysis tools (Manuscript, Readability,
  Project Word Count, Project Spellcheck, Word Frequency), file
  navigation, and the modes (Focus Mode, Split View, Read Aloud).
  Edit holds only operations on the text itself (find, replace,
  insert, split, merge, comments, bookmarks); File holds only
  file and project operations; Help holds only About.
- **Menu bar as the top bar** — there is no separate title bar:
  the menu bar is the top of the window, 38px tall, and it carries the minimize, maximize, and close buttons
  on its right. Drag its empty area to move the window,
  double-click it to maximize or restore, drag it to the top of
  the screen to maximize, and drag any edge or corner to resize.
  The app's name, "Novelshop", sits centered in the bar in muted
  grey, like a native window title; it ignores the mouse, so the
  window still drags from it, and it hides with the bar in Focus
  Mode. The close button turns red on hover, like Windows'. On
  Windows the frameless window also gets a native drop shadow, so
  it doesn't sit flat against the desktop. The window's corners are
  just rounded enough (2px) to take the square tip off, so the
  File menu and the caption buttons sit at the edges without the
  curve cutting into them. In Focus
  Mode the menu bar hides, so the buttons hide with it — Alt+F4
  still closes, and Esc or F11 brings the bar back.
- **About** — Help → About Novelshop... shows the app's name,
  its version (1.0.1), its creator (Andrew Kordula), and its
  license (GNU Lesser General Public License v2.1 or later), with
  a View License button that shows the full license text.

## How it's put together

One concern per file, small modules, data piped between them:

- `main.py` — entry point only: app, window, window icon.
- `novel_shop/about.py` — the About dialog (Help → About Novelshop...):
  the app's name, version, creator, and license, with a
  View License button that reads the LICENSE file in the project
  folder. The version lives in `novel_shop/__init__.py`
  (`__version__ = "1.0.1"`).
- `novel_shop/icon.png` / `novel_shop/icon.ico` — the "Ns" tile: a
  white rounded square with black capital + lowercase letters.
  The letters span ~84% of the tile's width at their natural
  proportions, about 48% tall.
  The .ico holds 16, 32, 48, and 256px versions for the taskbar and
  title bar; main.py sets it on the app. If the app is ever packaged
  with PyInstaller, pass `--icon novel_shop/icon.ico` to use the same
  tile for the .exe file itself.
- `novel_shop/wordcount.py` — pure word/character/line counting.
- `novel_shop/storage.py` — reading and writing text files.
- `novel_shop/session.py` — remembering the open folder and files.
- `novel_shop/snapshots.py` — dated backups of a document.
- `novel_shop/snapshot_dialog.py` — the snapshot browser dialog.
- `novel_shop/diff.py` — the snapshot diff: a unified diff as a
  colored page, and the dialog that shows it.
- `novel_shop/quick_open.py` — the Quick Open picker: the folder's
  files, filtered as you type.
- `novel_shop/read_aloud.py` — the system-voice read aloud: Qt's
  text-to-speech, wrapped so a missing engine or voice is a no-op, not an error.
- `novel_shop/piper_read_aloud.py` — the Piper (neural) read aloud:
  a worker thread synthesizes the text sentence by sentence to WAV
  files, and Qt's media player plays them in order. The voice is a
  model file the user picks; without one, this engine is unavailable.
- `novel_shop/manuscript_view.py` — the Manuscript view: the story
  files as one read-only document, in tree order.
- `novel_shop/manuscript.py` — assembling the folder into a manuscript.
- `novel_shop/exporters.py` — the DOCX, EPUB, and PDF writers.
- `novel_shop/export_dialog.py` — the Export window.
- `novel_shop/file_tree.py` — the folder tree widget (the binder).
- `novel_shop/file_types.py` — the file types: one place defines every
  extension, its tree group, and the New File dropdown.
- `novel_shop/new_file_dialog.py` — the New File window: name + type
  dropdown (Custom included).
- `novel_shop/rename_dialog.py` — the Rename window: the file's
  current name and type, pre-filled, with the same dropdown and the
  check that the new name does not already exist.
- `novel_shop/trash.py` — the Trash: moving a file to the project's
  `.trash` folder, restoring it, and emptying the Trash.
- `novel_shop/icons.py` — every icon in the app: Qt standard icons,
  plus the per-type badge icons drawn with QPainter.
  Never an OS icon: any new icon goes through this module.
- `novel_shop/find_bar.py` — the find & replace bar, with a regex
  toggle and `\1` backreferences in Replace All.
- `novel_shop/comments.py` — comments: notes pinned to a passage,
  stored in a sidecar JSON next to the document, anchored by the
  passage text so they follow it when the words around it move.
- `novel_shop/comments_dialog.py` — the Comments window: the file's
  notes, with add / edit / delete and jump-to-passage.
- `novel_shop/project_search.py` — searching every file in the folder,
  and replacing across them.
- `novel_shop/search_dialog.py` — the Find in Project window.
- `novel_shop/spellcheck.py` — the spell dictionary, which words are
  misspelled, and the suggestions. The underlines themselves are drawn
  by the highlighter (Qt only keeps one highlighter's formats per
  block, so the spell underlines and the entity colors share it).
- `novel_shop/lexicon.py` — the dictionary and thesaurus: WordNet
  lookups (definitions, synonyms, antonyms), loaded lazily so the
  app starts fine without WordNet installed.
- `novel_shop/reverse.py` — the reverse dictionary: an inverted
  index over WordNet definitions, built by reading WordNet's own
  database in bulk (a few seconds the first time, then instant),
  ranked by how many of the description's words a definition
  contains, rare words counting more.
- `novel_shop/lookup_dialog.py` — the Define dialog: the lookup
  results as a readable page.
- `novel_shop/lookup_window.py` — the Dictionary window: a general
  lookup with a search box, modeless, not tied to the editor. Also
  holds the Reverse search toggle and the candidate list.
  Synonyms in it are links that look the word up.
- `novel_shop/editor.py` — the writing surface + dirty tracking. Reads
  and writes Markdown with its own small parser, so the file
  round-trips exactly (Qt's Markdown support would collapse a single
  newline inside a paragraph to a space). Also the as-you-type smart
  quotes and dashes, Go to Line, Fix Typography, duplicate/move
  paragraph, change case, paste as plain text, zoom, block quotes,
  manual highlight, and text alignment (stored as an HTML div).
- `novel_shop/highlighter.py` — the syntax-style highlighter that
  colors mentions of defined things, underlines misspelled words,
  underlines overused words, and renders `# ` / `## ` headings
  larger and bold with the markers faded, and `> ` block quotes
  italic with the marker faded.
- `novel_shop/weasel_words.py` — the overused-words list and where
  they are in a text.
- `novel_shop/readability.py` — syllable counting and the
  Flesch-Kincaid grade and reading-ease formulas.
- `novel_shop/readability_dialog.py` — the Readability window.
- `novel_shop/project_stats.py` — the Project Word Count window:
  per-file counts and the whole-book total.
- `novel_shop/project_spellcheck.py` — the Project Spellcheck window:
  every misspelled word in the project, with counts and files, and
  click-to-jump to the first occurrence.
- `novel_shop/word_frequency.py` — the Word Frequency window: the
  book's most-used words (top 50), stopwords left out, with a filter
  box.
- `novel_shop/typography.py` — smart quotes and dashes: which curly
  quote fits where, and the edits that fix existing text.
- `novel_shop/theme.py` — the themes: "novelshop-dark" (a dark style
  sheet with a near-black palette and blue accent,
  editor dark too) and "novelshop-light" (the same design inverted:
  white editor, light grey chrome, near-black text, same blue
  accent), built from one parameterized sheet. `apply_theme` puts
  the sheet on the whole application, and `theme_background`
  gives the window's fill color for the rounded corners. It also
  holds the caption-button rules and `style_popup_menu`.
- `novel_shop/frameless.py` — the frameless window behavior:
  `CaptionButton` (the minimize / maximize / restore / close
  buttons, glyphs painted by hand), `DraggableMenuBar` (the menu
  bar is the top bar, 38px tall, carrying the caption buttons; drag its empty area to move, double-click to maximize,
  drag to the top to maximize), `EdgeResizer` (an
  application-level event filter that brings the resize handles
  back for a frameless window).
- `novel_shop/highlight_dialog.py` — the Highlight Colors window.
- `novel_shop/format_toolbar.py` — the font/size/bold/italic/underline/strikethrough/highlight toolbar.
- `novel_shop/preferences.py` — editor font, highlight colors, the
  user's dictionary words, and the spellcheck toggle, kept in AppData
  next to the session file.
- `novel_shop/document_tabs.py` — one tab per document: open, save,
  close, dirty markers.
- `novel_shop/main_window.py` — layout, menus, autosave, prompts.

## Third-party libraries

Novelshop is built on these open-source libraries. The app itself is
LGPLv2.1-or-later; each of these keeps its own license:

- [PySide6](https://github.com/qtproject/pyside-pyside-setup) — the
  whole user interface: the Qt framework's Python bindings. LGPL-3.0
  (also available under GPL).
- [python-docx](https://github.com/python-openxml/python-docx) — writes
  the DOCX export. MIT.
- [ebooklib](https://github.com/aerkalov/ebooklib) — writes the EPUB
  export. AGPL-3.0.
- [pyspellchecker](https://github.com/barrust/pyspellchecker) — the
  spellchecker: flags misspelled words and offers suggestions. MIT.
- [wn](https://github.com/goodmami/wn) — the dictionary and thesaurus:
  WordNet lookups (definitions, synonyms, antonyms) and the reverse
  dictionary. MIT.
- [piper-tts](https://github.com/OHF-Voice/piper1-gpl) — the Piper
  neural read-aloud voice. GPL-3.0.
- [onnxruntime](https://github.com/microsoft/onnxruntime) — runs the
  Piper voice model; it comes in through piper-tts. MIT.

The dictionary's word data is
[Open English WordNet](https://github.com/globalwordnet/english-wordnet)
(CC-BY 4.0), downloaded separately with `python -m wn download
ewn:2020`. The "Ns" logo lettering is
[Montserrat](https://github.com/JulietaUla/Montserrat) Bold
(SIL Open Font License), used at build time only.

## License

Novelshop is free software, licensed under the **GNU Lesser General
Public License, version 2.1** (LGPLv2.1), or (at your option) any
later version. The full license text is in `LICENSE`; each source
file carries the copyright notice at the top. That means anyone can
use, modify, and share the app, and changes to Novelshop itself
must be shared under the same terms — while a program that merely
uses it is not bound by it. LGPLv2.1 is compatible with the GPLv3
components the app can use (such as the Piper voice), so the two
can be distributed together.
