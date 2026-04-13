import pytest
from lore_core.distill import extract_symbols_from_diff

def test_extract_python_function_from_diff():
    diff = """--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,4 @@
 def existing_func():
     pass
+
+def new_func():
+    print("hello")
"""
    symbols = extract_symbols_from_diff(diff)
    assert "new_func" in symbols

def test_extract_python_class_from_diff():
    diff = """--- a/src/models.py
+++ b/src/models.py
@@ -1,5 +1,6 @@
+class NewModel:
+    pass
 """
    symbols = extract_symbols_from_diff(diff)
    assert "NewModel" in symbols

def test_extract_multiple_symbols():
    diff = """--- a/src/app.py
+++ b/src/app.py
@@ -1,10 +1,15 @@
+class Database:
+    def connect(self):
+        pass
+
+def run_app():
+    db = Database()
+    db.connect()
 """
    symbols = extract_symbols_from_diff(diff)
    assert "Database" in symbols
    assert "connect" in symbols
    assert "run_app" in symbols
