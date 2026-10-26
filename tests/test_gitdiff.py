"""Parsing changed lines out of `git diff --unified=0`."""

from healthkit.gitdiff import parse_changed_lines

# Real git output: a path containing a space gets a trailing TAB on its ---/+++ lines.
DIFF = """\
diff --git a/Bot Starter Kit/app/bot.py b/Bot Starter Kit/app/bot.py
index 1..2 100644
--- a/Bot Starter Kit/app/bot.py\t
+++ b/Bot Starter Kit/app/bot.py\t
@@ -1,0 +2,2 @@
+import os
+import sys
diff --git a/users/api/users.py b/users/api/users.py
--- a/users/api/users.py
+++ b/users/api/users.py
@@ -10 +10 @@ def f():
-    old
+    new
@@ -20,3 +19,0 @@
-gone
-gone
-gone
diff --git a/commons/utils.py b/commons/utils.py
--- a/commons/utils.py
+++ b/commons/utils.py
@@ -5,2 +4,0 @@
-unused_helper = None
-another = None
diff --git a/logo.png b/logo.png
Binary files a/logo.png and b/logo.png differ
diff --git a/gone.py b/gone.py
deleted file mode 100644
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-z = 3
"""


def test_added_and_changed_lines_per_file():
    changed = parse_changed_lines(DIFF)

    assert changed == {
        "Bot Starter Kit/app/bot.py": {2, 3},
        "users/api/users.py": {10},
    }


def test_a_pure_deletion_adds_no_lines():
    changed = parse_changed_lines(DIFF)

    assert "gone.py" not in changed
    assert "commons/utils.py" not in changed  # modified, but only by deleting lines
    assert all(lines for lines in changed.values())
