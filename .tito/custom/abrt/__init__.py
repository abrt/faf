from fileinput import FileInput
import os
import re
import shlex

from tito.common import info_out, run_command
from tito.tagger import VersionTagger


class Tagger(VersionTagger):
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
