# -*- coding: utf-8 -*-

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#
# documentation build configuration file, created by
# sphinx-quickstart on Thu Jul 23 19:40:08 2015.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
from functools import partial
import gc
from importlib import import_module
import inspect
from hashlib import md5
import os
from pathlib import Path
import re
import sys
from textwrap import dedent, indent
from typing import List
from unittest.mock import patch

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
curr_path = Path(__file__).expanduser().absolute().parent
if curr_path.name == "_staging":
    # Can't use curr_path.parent, because sphinx_gallery requires a relative path.
    tvm_path = Path(os.pardir, os.pardir)
else:
    tvm_path = Path(os.pardir)

sys.path.insert(0, str(tvm_path.resolve() / "python"))
sys.path.insert(0, str(tvm_path.resolve() / "vta" / "python"))
sys.path.insert(0, str(tvm_path.resolve() / "docs"))

# -- General configuration ------------------------------------------------

# General information about the project.
project = "tvm"
author = "Apache Software Foundation"
copyright = "2020 - 2023, %s" % author
github_doc_root = "https://github.com/apache/tvm/tree/main/docs/"

os.environ["TVM_BUILD_DOC"] = "1"


def git_describe_version(original_version):
    """Get git describe version."""
    ver_py = tvm_path.joinpath("version.py")
    libver = {"__file__": ver_py}
    exec(compile(open(ver_py, "rb").read(), ver_py, "exec"), libver, libver)
    _, gd_version = libver["git_describe_version"]()
    if gd_version != original_version:
        print("Use git describe based version %s" % gd_version)
    return gd_version


# Version information.
import tvm
from tvm import topi
from tvm import te
from tvm import testing

version = git_describe_version(tvm.__version__)
release = version


def monkey_patch(module_name, func_name):
    """Helper function for monkey-patching library functions.

    Used to modify a few sphinx-gallery behaviors to make the "Open in Colab" button work correctly.
    Should be called as a decorator with arguments. Note this behaves differently from unittest's
    @mock.patch, as our monkey_patch decorator should be placed on the new version of the function.
    """
    module = import_module(module_name)
    original_func = getattr(module, func_name)

    def decorator(function):
        updated_func = partial(function, real_func=original_func)
        setattr(module, func_name, updated_func)
        return updated_func

    return decorator


CURRENT_FILE_CONF = None


@monkey_patch("sphinx_gallery.py_source_parser", "split_code_and_text_blocks")
def split_code_and_text_blocks(source_file, return_node, real_func):
    """Monkey-patch split_code_and_text_blocks to expose sphinx-gallery's file-level config.

    It's kinda gross, but we need access to file_conf to detect the requires_cuda flag.
    """
    global CURRENT_FILE_CONF
    file_conf, blocks, node = real_func(source_file, return_node)
    CURRENT_FILE_CONF = file_conf
    return (file_conf, blocks, node)


# This header replaces the default sphinx-gallery one in sphinx_gallery/gen_rst.py.
COLAB_HTML_HEADER = """
.. DO NOT EDIT. THIS FILE WAS AUTOMATICALLY GENERATED BY
.. TVM'S MONKEY-PATCHED VERSION OF SPHINX-GALLERY. TO MAKE
.. CHANGES, EDIT THE SOURCE PYTHON FILE:
.. "{python_file}"

.. only:: html

    .. note::
        :class: sphx-glr-download-link-note

        This tutorial can be used interactively with Google Colab! You can also click
        :ref:`here <sphx_glr_download_{ref_name}>` to run the Jupyter notebook locally.

        .. image:: {button_svg}
            :align: center
            :target: {colab_url}
            :width: 300px

.. rst-class:: sphx-glr-example-title

.. _sphx_glr_{ref_name}:

"""

# Google Colab allows opening .ipynb files on GitHub by appending a GitHub path to this base URL.
COLAB_URL_BASE = "https://colab.research.google.com/github"

# The GitHub path where the site is automatically deployed by tvm-bot.
IPYTHON_GITHUB_BASE = "apache/tvm-site/blob/asf-site/docs/_downloads/"

# The SVG image of the "Open in Colab" button.
BUTTON = (
    "https://raw.githubusercontent.com/tlc-pack/web-data/main/images/utilities/colab_button.svg"
)


@monkey_patch("sphinx_gallery.gen_rst", "save_rst_example")
def save_rst_example(example_rst, example_file, time_elapsed, memory_used, gallery_conf, real_func):
    """Monkey-patch save_rst_example to include the "Open in Colab" button."""

    # The url is the md5 hash of the notebook path.
    example_fname = os.path.relpath(example_file, gallery_conf["src_dir"])
    ref_fname = example_fname.replace(os.path.sep, "_")
    notebook_path = example_fname[:-2] + "ipynb"
    digest = md5(notebook_path.encode()).hexdigest()

    # Fixed documentation versions must link to different (earlier) .ipynb notebooks.
    colab_url = f"{COLAB_URL_BASE}/{IPYTHON_GITHUB_BASE}"
    if "dev" not in version:
        colab_url += version + "/"
    colab_url += digest + "/" + os.path.basename(notebook_path)

    new_header = COLAB_HTML_HEADER.format(
        python_file=example_fname, ref_name=ref_fname, colab_url=colab_url, button_svg=BUTTON
    )
    with patch("sphinx_gallery.gen_rst.EXAMPLE_HEADER", new_header):
        real_func(example_rst, example_file, time_elapsed, memory_used, gallery_conf)


INCLUDE_DIRECTIVE_RE = re.compile(r"^([ \t]*)\.\. include::\s*(.+)\n", flags=re.M)
COMMENT_DIRECTIVE_RE = re.compile(r"^\.\.(?: .*)?\n(?:(?:  .*)?\n)*", flags=re.M)
ADMONITION_DIRECTIVE_RE = re.compile(rf"^\.\. admonition:: *(.*)\n((?:(?:  .*)?\n)*)\n", flags=re.M)


@monkey_patch("sphinx_gallery.notebook", "rst2md")
def rst2md(text, gallery_conf, target_dir, heading_levels, real_func):
    """Monkey-patch rst2md to support comments and some include directives.

    Currently, only include directives without any parameters are supported. Also, note that in
    reStructuredText any unrecognized explicit markup block is treated as a comment (see
    https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#comments).

    For callouts, we only replace generic "admonition" directives. All others should be replaced by
    sphinx-gallery's rst2md. Note that the "alert" and "alert-info" tags are support in most IPython
    notebooks, but they render kinda funky on Colab.
    """

    def load_include(match):
        full_path = os.path.join(target_dir, match.group(2))
        with open(full_path) as f:
            lines = f.read()
        indented = indent(lines, match.group(1)) + "\n"
        return indented

    text = re.sub(INCLUDE_DIRECTIVE_RE, load_include, text)

    # Replace generic, titled admonitions with indented text. Other admonitions (e.g. .. note::)
    # will be handled by sphinx-gallery's
    def rewrite_generic_admonition(match):
        title, text = match.groups()
        stripped_text = dedent(text).strip()
        return f'<div class="alert alert-info"><h4>{title}</h4><p>{stripped_text}</p></div>'

    text = re.sub(ADMONITION_DIRECTIVE_RE, rewrite_generic_admonition, text)

    # Call the real function, and then strip any remaining directives (i.e. comments)
    text = real_func(text, gallery_conf, target_dir, heading_levels)
    text = re.sub(COMMENT_DIRECTIVE_RE, "", text)
    return text


def install_request_hook(gallery_conf, fname):
    testing.utils.install_request_hook(depth=3)


INSTALL_TVM_DEV = f"""\
%%shell
# Installs the latest dev build of TVM from PyPI. If you wish to build
# from source, see https://tvm.apache.org/docs/install/from_source.html
pip install apache-tvm --pre"""

INSTALL_TVM_FIXED = f"""\
%%shell
# Installs TVM version {version} from PyPI. If you wish to build
# from source, see https://tvm.apache.org/docs/install/from_source.html
pip install apache-tvm=={version}"""

INSTALL_TVM_CUDA_DEV = f"""\
%%shell
# Installs the latest dev build of TVM from PyPI, with CUDA enabled. To use this,
# you must request a Google Colab instance with a GPU by going to Runtime ->
# Change runtime type -> Hardware accelerator -> GPU. If you wish to build from
# source, see https://tvm.apache.org/docs/install/from_source.html
pip install tlcpack-nightly-cu113 --pre -f https://tlcpack.ai/wheels"""

INSTALL_TVM_CUDA_FIXED = f"""\
%%shell
# Installs TVM version {version} from PyPI, with CUDA enabled. To use this,
# you must request a Google Colab instance with a GPU by going to Runtime ->
# Change runtime type -> Hardware accelerator -> GPU. If you wish to build from
# source, see https://tvm.apache.org/docs/install/from_source.html
pip install apache-tvm-cu113=={version} --no-index  -f https://tlcpack.ai/wheels"""


@monkey_patch("sphinx_gallery.gen_rst", "jupyter_notebook")
def jupyter_notebook(script_blocks, gallery_conf, target_dir, real_func):
    """Monkey-patch sphinx-gallery to add a TVM import block to each IPython notebook.

    If we had only one import block, we could skip the patching and just set first_notebook_cell.
    However, how we import TVM depends on if we are using a fixed or dev version, and whether we
    will use the GPU.

    Tutorials requiring a CUDA-enabled build of TVM should use the flag:
    # sphinx_gallery_requires_cuda = True
    """

    requires_cuda = CURRENT_FILE_CONF.get("requires_cuda", False)
    fixed_version = not "dev" in version

    if fixed_version and requires_cuda:
        install_block = INSTALL_TVM_CUDA_FIXED
    elif fixed_version and not requires_cuda:
        install_block = INSTALL_TVM_FIXED
    elif not fixed_version and requires_cuda:
        install_block = INSTALL_TVM_CUDA_DEV
    else:
        install_block = INSTALL_TVM_DEV

    new_conf = {**gallery_conf, "first_notebook_cell": install_block}
    return real_func(script_blocks, new_conf, target_dir)


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx_gallery.gen_gallery",
    "autodocsumm",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = [".rst", ".md"]

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# generate autosummary even if no references
autosummary_generate = True

# The main toctree document.
main_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "_staging"]

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme is set by the make target
html_theme = os.environ.get("TVM_THEME", "rtd")

on_rtd = os.environ.get("READTHEDOCS", None) == "True"
# only import rtd theme and set it if want to build docs locally
if not on_rtd and html_theme == "rtd":
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_theme_options = {
    "analytics_id": "UA-75982049-2",
    "logo_only": True,
}

html_logo = "_static/img/tvm-logo-small.png"

html_favicon = "_static/img/tvm-logo-square.png"


# Output file base name for HTML help builder.
htmlhelp_basename = project + "doc"

# -- Options for LaTeX output ---------------------------------------------
latex_elements = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (main_doc, "%s.tex" % project, project, author, "manual"),
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/{.major}".format(sys.version_info), None),
    # "numpy": ("https://numpy.org/doc/stable", None),
    # "scipy": ("https://docs.scipy.org/doc/scipy", None),
    # "matplotlib": ("https://matplotlib.org/", None),
}

from sphinx_gallery.sorting import ExplicitOrder

examples_dirs = [
    # legacy tutorial structure under gallery folder
    tvm_path.joinpath("gallery", "tutorial"),
    tvm_path.joinpath("gallery", "how_to", "compile_models"),
    tvm_path.joinpath("gallery", "how_to", "deploy_models"),
    tvm_path.joinpath("gallery", "how_to", "work_with_relay"),
    tvm_path.joinpath("gallery", "how_to", "work_with_schedules"),
    tvm_path.joinpath("gallery", "how_to", "optimize_operators"),
    tvm_path.joinpath("gallery", "how_to", "tune_with_autotvm"),
    tvm_path.joinpath("gallery", "how_to", "tune_with_autoscheduler"),
    tvm_path.joinpath("gallery", "how_to", "work_with_microtvm"),
    tvm_path.joinpath("gallery", "how_to", "extend_tvm"),
    tvm_path.joinpath("vta", "tutorials"),
    # New tutorial structure under docs folder
    tvm_path.joinpath("docs", "get_started", "tutorials"),
    tvm_path.joinpath("docs", "how_to", "tutorials"),
    tvm_path.joinpath("docs", "deep_dive", "tensor_ir", "tutorials"),
]

gallery_dirs = [
    # legacy tutorial structure under gallery folder
    "tutorial",
    "how_to/compile_models",
    "how_to/deploy_models",
    "how_to/work_with_relay",
    "how_to/work_with_schedules",
    "how_to/optimize_operators",
    "how_to/tune_with_autotvm",
    "how_to/tune_with_autoscheduler",
    "how_to/work_with_microtvm",
    "how_to/extend_tvm",
    "topic/vta/tutorials",
    # New tutorial structure under docs folder
    "get_started/tutorials/",
    "how_to/tutorials/",
    "deep_dive/tensor_ir/tutorials/",
]


subsection_order = ExplicitOrder(
    str(p)
    for p in [
        tvm_path / "vta" / "tutorials" / "frontend",
        tvm_path / "vta" / "tutorials" / "optimize",
    ]
)

# Explicitly define the order within a subsection.
# The listed files are sorted according to the list.
# The unlisted files are sorted by filenames.
# The unlisted files always appear after listed files.
within_subsection_order = {
    "tutorial": [
        "introduction.py",
        "install.py",
        "tvmc_command_line_driver.py",
        "tvmc_python.py",
        "autotvm_relay_x86.py",
        "tensor_expr_get_started.py",
        "autotvm_matmul_x86.py",
        "auto_scheduler_matmul_x86.py",
        "tensor_ir_blitz_course.py",
        "topi.pi",
        "cross_compilation_and_rpc.py",
        "relay_quick_start.py",
        "uma.py",
    ],
    "compile_models": [
        "from_pytorch.py",
        "from_tensorflow.py",
        "from_mxnet.py",
        "from_onnx.py",
        "from_keras.py",
        "from_tflite.py",
        "from_coreml.py",
        "from_darknet.py",
        "from_caffe2.py",
        "from_paddle.py",
    ],
    "work_with_schedules": [
        "schedule_primitives.py",
        "reduction.py",
        "scan.py",
        "extern_op.py",
        "tensorize.py",
        "tuple_inputs.py",
        "tedd.py",
    ],
    "optimize_operators": [
        "opt_gemm.py",
        "opt_conv_cuda.py",
        "opt_conv_tensorcore.py",
    ],
    "tune_with_autotvm": [
        "tune_conv2d_cuda.py",
        "tune_relay_cuda.py",
        "tune_relay_x86.py",
        "tune_relay_arm.py",
        "tune_relay_mobile_gpu.py",
    ],
    "tune_with_autoscheduler": [
        "tune_matmul_x86.py",
        "tune_conv2d_layer_cuda.py",
        "tune_network_x86.py",
        "tune_network_cuda.py",
    ],
    "extend_tvm": [
        "low_level_custom_pass.py",
        "use_pass_infra.py",
        "use_pass_instrument.py",
        "bring_your_own_datatypes.py",
    ],
    "work_with_microtvm": [
        "micro_tvmc.py",
        "micro_tflite.py",
        "micro_aot.py",
        "micro_pytorch.py",
        "micro_train.py",
        "micro_autotune.py",
        "micro_ethosu.py",
        "micro_mlperftiny.py",
    ],
}


class WithinSubsectionOrder:
    def __init__(self, src_dir):
        self.src_dir = src_dir.split("/")[-1]

    def __call__(self, filename):
        # If the order is provided, use the provided order
        if (
            self.src_dir in within_subsection_order
            and filename in within_subsection_order[self.src_dir]
        ):
            index = within_subsection_order[self.src_dir].index(filename)
            assert index < 1e10
            return "\0%010d" % index

        # Otherwise, sort by filename
        return filename


# When running the tutorials on GPUs we are dependent on the Python garbage collector
# collecting TVM packed function closures for any device memory to also be released. This
# is not a good setup for machines with lots of CPU ram but constrained GPU ram, so force
# a gc after each example.
def force_gc(gallery_conf, fname):
    gc.collect()


# Skips certain files to avoid dependency issues
filename_pattern_default = "^(?!.*micro_mlperftiny.py).*$"

sphinx_gallery_conf = {
    "backreferences_dir": "gen_modules/backreferences",
    "doc_module": ("tvm", "numpy"),
    "reference_url": {
        "tvm": None,
        # "matplotlib": "https://matplotlib.org/",
        # "numpy": "https://numpy.org/doc/stable",
    },
    "examples_dirs": examples_dirs,
    "within_subsection_order": WithinSubsectionOrder,
    "gallery_dirs": gallery_dirs,
    "subsection_order": subsection_order,
    "filename_pattern": os.environ.get("TVM_TUTORIAL_EXEC_PATTERN", filename_pattern_default),
    "download_all_examples": False,
    "min_reported_time": 60,
    "expected_failing_examples": [],
    "reset_modules": ("matplotlib", "seaborn", force_gc),
    "promote_jupyter_magic": True,
    "reset_modules": (install_request_hook),
}

autodoc_default_options = {
    "member-order": "bysource",
}

# Maps the original namespace to list of potential modules
# that we can import alias from.
tvm_alias_check_map = {
    "tvm.te": ["tvm.tir"],
    "tvm.tir": ["tvm.ir", "tvm.runtime"],
    "tvm.relay": ["tvm.ir", "tvm.tir"],
}

## Setup header and other configs
import tlcpack_sphinx_addon

footer_copyright = "© 2023 Apache Software Foundation | All rights reserved"
footer_note = " ".join(
    """
Copyright © 2023 The Apache Software Foundation. Apache TVM, Apache, the Apache feather,
and the Apache TVM project logo are either trademarks or registered trademarks of
the Apache Software Foundation.""".split(
        "\n"
    )
).strip()

header_logo = "https://tvm.apache.org/assets/images/logo.svg"
header_logo_link = "https://tvm.apache.org/"

header_links = [
    ("Community", "https://tvm.apache.org/community"),
    ("Download", "https://tvm.apache.org/download"),
    ("VTA", "https://tvm.apache.org/vta"),
    ("Blog", "https://tvm.apache.org/blog"),
    ("Docs", "https://tvm.apache.org/docs"),
    ("Conference", "https://tvmconf.org"),
    ("Github", "https://github.com/apache/tvm/"),
]

header_dropdown = {
    "name": "ASF",
    "items": [
        ("Apache Homepage", "https://apache.org/"),
        ("License", "https://www.apache.org/licenses/"),
        ("Sponsorship", "https://www.apache.org/foundation/sponsorship.html"),
        ("Security", "https://www.apache.org/security/"),
        ("Thanks", "https://www.apache.org/foundation/thanks.html"),
        ("Events", "https://www.apache.org/events/current-event"),
    ],
}


def fixup_tutorials(original_url: str) -> str:
    if "docs/tutorial" in original_url:
        # tutorials true source is in Python or .txt files, but Sphinx only sees
        # the generated .rst files so this maps them back to the source
        if original_url.endswith("index.rst"):
            # for index pages, go to the README files
            return re.sub(
                r"docs/tutorial/(.*)index\.rst", "gallery/tutorial/\\1README.txt", original_url
            )
        else:
            # otherwise for tutorials, redirect to python files
            return re.sub(r"docs/tutorial/(.*)\.rst", "gallery/tutorial/\\1.py", original_url)
    else:
        # do nothing for normal non-tutorial .rst files
        return original_url


html_context = {
    "footer_copyright": footer_copyright,
    "footer_note": footer_note,
    "header_links": header_links,
    "header_dropdown": header_dropdown,
    "header_logo": header_logo,
    "header_logo_link": header_logo_link,
    "version_prefixes": [
        "main",
        "v0.8.0/",
        "v0.9.0/",
        "v0.10.0/",
        "v0.11.0/",
        "v0.12.0/",
        "v0.13.0/",
        "v0.14.0/",
        "v0.15.0/",
        "v0.16.0/",
    ],
    "display_github": True,
    "github_user": "apache",
    "github_repo": "tvm",
    "github_version": "main/docs/",
    "theme_vcs_pageview_mode": "edit",
    "edit_link_hook_fn": fixup_tutorials,
}

# add additional overrides
templates_path += [tlcpack_sphinx_addon.get_templates_path()]
html_static_path += [tlcpack_sphinx_addon.get_static_path()]


def update_alias_docstring(name, obj, lines):
    """Update the docstring of alias functions.

    This function checks if the obj is an alias of another documented object
    in a different module.

    If it is an alias, then it will append the alias information to the docstring.

    Parameters
    ----------
    name : str
        The full name of the object in the doc.

    obj : object
        The original object.

    lines : list
        The docstring lines, need to be modified inplace.
    """
    arr = name.rsplit(".", 1)
    if len(arr) != 2:
        return
    target_mod, target_name = arr

    if target_mod not in tvm_alias_check_map:
        return
    if not hasattr(obj, "__module__"):
        return
    obj_mod = obj.__module__

    for amod in tvm_alias_check_map[target_mod]:
        if not obj_mod.startswith(amod):
            continue

        if hasattr(sys.modules[amod], target_name):
            obj_type = ":py:func" if callable(obj) else ":py:class"
            lines.append(".. rubric:: Alias of %s:`%s.%s`" % (obj_type, amod, target_name))


tvm_class_name_rewrite_map = {
    "tvm.tir": ["Var", "Call"],
    "tvm.relax": ["Var", "Call"],
    "tvm.relax.frontend.nn": ["Module"],
}


def distinguish_class_name(name: str, lines: List[str]):
    """Distinguish the docstring of type annotations.

    In the whole TVM, there are many classes with the same name but in different modules,
    e.g. ``tir.Var``, ``relax.Var``. This function is used to distinguish them in the docstring,
    by adding the module name as prefix.

    To be specific, this function will check the current object name, and if it in the specific
    module with specific name, it will add the module name as prefix to the class name to prevent
    the confusion. Further, we only add the prefix to those standalone class name, but skip
    the pattern of `xx.Var`, `Var.xx` and `xx.Var.xx`.

    Parameters
    ----------
    name : str
        The full name of the object in the doc.

    lines : list
        The docstring lines, need to be modified inplace.
    """
    remap = {}
    for module_name in tvm_class_name_rewrite_map:
        if name.startswith(module_name):
            short_name = module_name[4:] if module_name.startswith("tvm.") else module_name
            for class_name in tvm_class_name_rewrite_map[module_name]:
                remap.update({class_name: f"{short_name}.{class_name}"})

    for k, v in remap.items():
        for i in range(len(lines)):
            lines[i] = re.sub(rf"(?<!\.)\b{k}\b(?!\.)", v, lines[i])


def process_docstring(app, what, name, obj, options, lines):
    """Sphinx callback to process docstring"""
    if callable(obj) or inspect.isclass(obj):
        update_alias_docstring(name, obj, lines)
        distinguish_class_name(name, lines)


from legacy_redirect import build_legacy_redirect


def strip_ipython_magic(app, docname, source):
    """Prevents IPython magic commands from being rendered in HTML files.

    TODO rework this function to remove IPython magic commands from include directives too.
    """
    for i in range(len(source)):
        source[i] = re.sub(r"%%.*\n\s*", "", source[i])


def setup(app):
    app.connect("source-read", strip_ipython_magic)
    app.connect("autodoc-process-docstring", process_docstring)
    app.connect("build-finished", build_legacy_redirect(tvm_path))
