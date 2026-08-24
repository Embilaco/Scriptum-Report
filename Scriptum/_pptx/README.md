# Subfolder overview
This is the pptx part o the main module and collects all functions and modules that are specific to pptx

## Usage and Test Instructions
- This folder requires python-pptx to be installed.
- Tests live under tests/: the pptx cases in tests/02_basetest/pptx-basic/ (each with a test_*.py that builds the deck and compares it with its expected/ reference) and the full example in tests/04_examples/pptreport/.
  
## Organization
- the module `reportPptx.py` is the main entry
- `base.py` contains the base class "PptElement"
- the modules for Images, Paragraphs/Texts, Tables are pairwise organized in "simple" Elements and "more complex" Templates


