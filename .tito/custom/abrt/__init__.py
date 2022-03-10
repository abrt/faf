import os
import re
import shlex
from datetime import date
from fileinput import FileInput

from tito.common import info_out, run_command
from tito.tagger import VersionTagger


class Tagger(VersionTagger):
    CHANGELOG_FILE = 'CHANGELOG.md'

    def _update_changelog(self, new_version: str):
        """
        Update changelog with the new version. This entails renaming headings
        in the Markdown file and updating links to compare the corresponding
        commits on GitHub.
        """
        with FileInput(self.CHANGELOG_FILE, inplace=True) as changelog:
            for line in changelog:
                if line.startswith('## [Unreleased]'):
                    # Add a heading for the release right below "Unreleased",
                    # inheriting its contents. This means that changes that were
                    # unreleased until now have become released in this new version.
                    release_date = date.today().strftime('%Y-%m-%d')
                    line += f'\n## [{new_version}] - {release_date}\n'
                elif line.startswith('[Unreleased]:'):
                    # Update link to comparison of changes on GitHub.
                    match = re.search(r'(https://.+/compare/)(.+)\.\.\.HEAD', line)
                    assert match is not None
                    url_prefix = match[1]
                    old_version = match[2]
                    line = (f'[Unreleased]: {url_prefix}{new_version}...HEAD\n'
                            f'[{new_version}]: {url_prefix}{old_version}...{new_version}\n')

                print(line, end='')

        run_command(f'git add -- {self.CHANGELOG_FILE}')

    def _bump_version(self, release=False, zstream=False):
        version = super()._bump_version().split('-', maxsplit=1)[0]
        pattern = re.compile(r'(?<=^m4_define\(\[faf_version\], \[)'
                             r'.*'
                             r'(?=\]\))')

        with FileInput(files='configure.ac', inplace=True) as input:
            for line in input:
                if pattern.search(line):
                    line = pattern.sub(version, line)

                print(line, end='')

        return version

    def _tag_release(self):
        version = self._bump_version()

        self._check_tag_does_not_exist(version)
        self._update_changelog(version)
        self._clear_package_metadata()

        metadata_file = os.path.join(self.rel_eng_dir, 'packages', self.project_name)

        with open(metadata_file, 'w') as file:
            file.write('%s %s\n' % (version, self.relative_project_dir))

        files = [
            metadata_file,
            os.path.join(self.full_project_dir, self.spec_file_name),
            'configure.ac',
        ]
        run_command('git add -- %s' % (' '.join([shlex.quote(file) for file in files])))

        message = 'Release version %s' % (version)

        run_command('git commit --message="%s"' % message)
        run_command('git tag --message="%s" %s' % (message, version))

        info_out('%s tagged' % version)
