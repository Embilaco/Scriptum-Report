# # Run all Scriptum tests
# 
# Use this notebook to execute the full pytest suite from a Jupyter environment. 
# 
# We do separate the different tests for now, otherwise the will interfer

# %%
from pathlib import Path
import os, sys
import subprocess
curdir = Path.cwd()

def runTestInDir(dir, opt="-q"):
    os.chdir(dir)
    print(f'run tests in {dir}')
    result = subprocess.run([sys.executable, "-m", "pytest", ".", opt], capture_output=True, text=True)
    print(result.stdout)

# %%
runTestInDir(curdir / '02_basetest' / 'yaml_loader')

# %%
runTestInDir(curdir / '02_basetest' / 'values' )

# %%
runTestInDir(curdir / '02_basetest' / 'parameter' )

# %%
runTestInDir(curdir / '02_basetest' / 'docx_basic' , opt="-v")

# %%
runTestInDir(curdir / '02_basetest' / 'pptx-basic' , opt="-v")

# %%
runTestInDir(curdir / '04_examples' )

# %%



