project = 'damex.cloudflare'
copyright = 'Roman Kuzmitskii'
title = 'damex.cloudflare Ansible Collection'
html_short_title = 'damex.cloudflare'

extensions = ['sphinx.ext.intersphinx', 'sphinx_antsibull_ext']
pygments_style = 'ansible'
highlight_language = 'YAML+Jinja'
default_role = 'any'
nitpicky = True

html_theme = 'sphinx_ansible_theme'
html_show_sphinx = False
html_use_smartypants = True
html_use_modindex = False
html_use_index = False
html_copy_source = False
display_version = False

intersphinx_mapping = {
    'python3': ('https://docs.python.org/3/', None),
    'ansible_devel': ('https://docs.ansible.com/projects/ansible/devel/', None),
}
