'''
Created on 28. jul. 2017

@author: mmpe
'''
import os
import subprocess


def _run_git_cmd(cmd, git_repo_path=None):
    git_repo_path = git_repo_path or os.getcwd()
    if not os.path.isdir(os.path.join(git_repo_path, ".git")):
        raise Warning("'%s' does not appear to be a Git repository." % git_repo_path)
    try:
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   universal_newlines=True,
                                   cwd=os.path.abspath(git_repo_path))
        stdout = process.communicate()[0]
        if process.returncode != 0:
            raise EnvironmentError()
        return stdout.strip()

    except EnvironmentError as e:
        raise e
        raise Warning("unable to run git")


def get_git_version(git_repo_path=None):
    cmd = ["git", "describe", "--tags", "--dirty", "--always"]
    return _run_git_cmd(cmd, git_repo_path)


def get_tag(git_repo_path=None):
    return _run_git_cmd(['git', 'describe', '--tags', '--abbrev=0'], git_repo_path)


def set_tag(tag, push, git_repo_path=None):
    _run_git_cmd(["git", "tag", tag], git_repo_path)
    if push:
        _run_git_cmd(["git", "push"], git_repo_path)
        _run_git_cmd(["git", "push", "--tags"], git_repo_path)


def update_git_version(version_module, git_repo_path=None):
    """Update <version_module>.__version__ to git version"""

    version_str = get_git_version(git_repo_path)
    assert os.path.isfile(version_module.__file__)
    with open(version_module.__file__, "w") as fid:
        fid.write("__version__ = '%s'" % version_str)

    # ensure file is written, closed and ready
    with open(version_module.__file__) as fid:
        fid.read()
    return version_str

def write_vers(vers_file='wetb/__init__.py'):
    version = get_tag(os.getcwd())
    print('Writing version: {} in {}'.format(version, vers_file))
    with open(vers_file, 'r') as f:
        lines = f.readlines()
    for n,l in enumerate(lines):
        if l.startswith('__version__'):
            lines[n] = "__version__ = '{}'\n".format(version[1:])
    with open(vers_file, 'w') as f:
        f.write(''.join(lines))
		
def rename_dist_file():
    for f in os.listdir('dist'):
        if f.endswith('whl'):
            split = f.split('linux')
            new_name = 'manylinux1'.join(split)
            old_path = os.path.join('dist',f)
            new_path = os.path.join('dist',new_name)
            os.rename(old_path, new_path)
    

def main():
    """Example of how to run (pytest-friendly)"""
    if __name__ == '__main__':
#        pass
#        import version
#        import app_utils
#        git_path = os.path.dirname(app_utils.__file__) + "/../"
#        update_git_version(version, git_path)
#        tag = get_tag(os.getcwd())
#        print(tag)
#        version = get_git_version(os.getcwd())
#        print(version)
#        rename_dist_file()
        write_vers()


main()
